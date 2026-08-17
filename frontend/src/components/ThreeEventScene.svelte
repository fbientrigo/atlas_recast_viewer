<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import type { CutKind, DetectorGeometry, EventRecord } from '../data/schema';
  import { directionEndpoint3d } from '../core/geometry';
  import { targetKey, type InspectionTarget } from '../core/inspection';

  export let events: EventRecord[] = [];
  export let geometry: DetectorGeometry;
  export let selectedCutId: string;
  export let selectedCutKind: CutKind;
  export let selectedEventId: number | null = null;
  export let selectedVertexIndex = 0;
  export let showDetector = true;
  export let showAnalysis = true;
  export let showResponse = false;
  export let selectedTarget: InspectionTarget | null = null;
  export let onInspect: (target: InspectionTarget) => void;
  export let onHover: (target: InspectionTarget | null) => void;

  let host: HTMLDivElement;
  let renderer: THREE.WebGLRenderer;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let controls: OrbitControls;
  let dynamic = new THREE.Group();
  let observer: ResizeObserver;
  let frame = 0;
  let ready = false;
  let cameraCutId = '';
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let pointerStart = { x: 0, y: 0 };

  const passColor = 0x18786d;
  const failColor = 0xc65a43;
  const selectedColor = 0xf2b134;

  function line(points: THREE.Vector3[], material: THREE.Material): THREE.Line {
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
  }

  function circle(radius: number, zExtent: number, material: THREE.Material): THREE.LineLoop {
    const points = Array.from({ length: 96 }, (_, i) => {
      const angle = i / 96 * Math.PI * 2;
      return new THREE.Vector3(radius * Math.cos(angle), radius * Math.sin(angle), zExtent);
    });
    const loop = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), material);
    if (material instanceof THREE.LineDashedMaterial) loop.computeLineDistances();
    return loop;
  }

  function shell(radius: number, halfLength: number, material: THREE.Material): THREE.Mesh {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, halfLength * 2, 64, 1, true), material);
    mesh.rotation.x = Math.PI / 2;
    return mesh;
  }

  function outlinedShell(radius: number, halfLength: number, color: number, opacity: number): THREE.Group {
    const group = new THREE.Group();
    group.add(shell(radius, halfLength, new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide, depthWrite: false })));
    group.add(circle(radius, -halfLength, new THREE.LineBasicMaterial({ color, transparent: true, opacity: Math.min(1, opacity * 4) })));
    group.add(circle(radius, halfLength, new THREE.LineBasicMaterial({ color, transparent: true, opacity: Math.min(1, opacity * 4) })));
    return group;
  }

  function makeInspectable(object: THREE.Object3D, target: InspectionTarget): void {
    object.userData.inspectionTarget = target;
    object.traverse((child) => { child.userData.inspectionTarget = target; });
  }

  function clearDynamic(): void {
    dynamic.traverse((object) => {
      if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.LineLoop) {
        object.geometry.dispose();
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach((material) => material.dispose());
      }
    });
    dynamic.clear();
  }

  function rebuild(): void {
    if (!ready) return;
    clearDynamic();
    const innerFocus = ['rxy_gt_4_mm', 'd0_gt_2_mm', 'tracks_ge_5', 'mdv_gt_10_gev'].includes(selectedCutId);
    const hardware = geometry.landmarks.filter((item) => item.kind === 'detector_hardware' && item.radius_mm !== null && (!innerFocus || item.id !== 'sct_barrel_1'));
    const analysis = geometry.landmarks.filter((item) => item.kind === 'analysis_boundary' && (
      selectedCutId === 'fiducial_dv' ? item.id === 'dv_max_r' || item.id === 'dv_max_z'
        : innerFocus ? item.id === 'dv_min_r' : false
    ));
    const response = geometry.landmarks.filter((item) => item.kind === 'response_bin' && item.radius_mm !== null);
    const displayHalfLength = Math.max(1, ...geometry.landmarks.map((item) => item.z_extent_mm ?? item.abs_z_mm ?? 0));
    const fiducialRadius = geometry.landmarks.find((item) => item.id === 'dv_max_r')?.radius_mm ?? 1;

    if (showDetector) for (const item of hardware) {
      const selected = targetKey(selectedTarget) === `layer:${item.id}`;
      const object = outlinedShell(item.radius_mm!, item.z_extent_mm ?? displayHalfLength, selected ? 0x426879 : 0x94a3ad, selected ? 0.16 : item.id === 'beam_pipe' ? 0.10 : 0.035);
      makeInspectable(object, { kind: 'layer', landmarkId: item.id });
      dynamic.add(object);
    }
    if (showAnalysis) for (const item of analysis) {
      const selected = targetKey(selectedTarget) === `layer:${item.id}`;
      const emphasized = selected || (selectedCutId === 'rxy_gt_4_mm' && item.id === 'dv_min_r') || (selectedCutId === 'fiducial_dv' && (item.id === 'dv_max_r' || item.id === 'dv_max_z'));
      if (item.radius_mm !== null) {
        const object = outlinedShell(item.radius_mm, item.z_extent_mm ?? displayHalfLength, item.id === 'dv_min_r' ? 0xe04f2f : 0xd67b16, emphasized ? 0.13 : 0.025);
        makeInspectable(object, { kind: 'layer', landmarkId: item.id });
        dynamic.add(object);
      }
      if (item.abs_z_mm) {
        for (const sign of [-1, 1]) {
          const disc = new THREE.Mesh(new THREE.CircleGeometry(fiducialRadius, 64), new THREE.MeshBasicMaterial({ color: 0xd67b16, transparent: true, opacity: emphasized ? 0.08 : 0.025, side: THREE.DoubleSide, depthWrite: false }));
          disc.position.z = sign * item.abs_z_mm;
          makeInspectable(disc, { kind: 'layer', landmarkId: item.id });
          dynamic.add(disc);
        }
      }
    }
    if (showResponse) for (const item of response) {
      const material = new THREE.LineDashedMaterial({ color: 0x8295a0, transparent: true, opacity: 0.35, dashSize: 3, gapSize: 3 });
      const object = circle(item.radius_mm!, 0, material);
      makeInspectable(object, { kind: 'layer', landmarkId: item.id });
      dynamic.add(object);
    }

    dynamic.add(line([new THREE.Vector3(0, 0, -340), new THREE.Vector3(0, 0, 340)], new THREE.LineBasicMaterial({ color: 0x49545b })));
    for (const event of events) {
      const responseStage = selectedCutKind === 'response_weight' || selectedCutKind === 'summary';
      const eventPasses = selectedCutId === 'jet_selection'
        ? event.predicates.jet_selection
        : event.vertices.some((vertex) => vertex.predicates[selectedCutId] === true);
      event.vertices.forEach((vertex, vertexIndex) => {
        const isSelected = event.event_id === selectedEventId && vertexIndex === selectedVertexIndex;
        const vertexPasses = selectedCutId === 'jet_selection' ? eventPasses : vertex.predicates[selectedCutId] === true;
        const color = isSelected ? selectedColor : responseStage ? 0x71858e : vertexPasses ? passColor : failColor;
        const flight = line(
          [new THREE.Vector3(0, 0, 0), new THREE.Vector3(vertex.x_mm, vertex.y_mm, vertex.z_mm)],
          new THREE.LineBasicMaterial({ color, transparent: true, opacity: isSelected ? 0.95 : 0.38 }),
        );
        dynamic.add(flight);
        const marker = new THREE.Mesh(
          new THREE.SphereGeometry(isSelected ? 3.4 : 2.1, 18, 12),
          new THREE.MeshBasicMaterial({ color, transparent: true, opacity: isSelected ? 1 : 0.82 }),
        );
        marker.position.set(vertex.x_mm, vertex.y_mm, vertex.z_mm);
        makeInspectable(marker, { kind: 'vertex', eventId: event.event_id, vertexIndex });
        dynamic.add(marker);

        if (isSelected) {
          for (const [trackIndex, track] of vertex.tracks.entries()) {
            const endpoint = directionEndpoint3d(
              { x: track.x_prod_mm, y: track.y_prod_mm, z: track.z_prod_mm },
              { px: track.px_GeV, py: track.py_GeV, pz: track.pz_GeV }, 70,
            );
            const trackSelected = targetKey(selectedTarget) === `track:${event.event_id}:${vertexIndex}:${trackIndex}`;
            const trackObject = line(
              [new THREE.Vector3(track.x_prod_mm, track.y_prod_mm, track.z_prod_mm), new THREE.Vector3(endpoint.x, endpoint.y, endpoint.z)],
              new THREE.LineBasicMaterial({ color: trackSelected ? 0xf2b134 : track.selected_for_dv ? 0x226f92 : 0x9aa7ae, transparent: true, opacity: trackSelected ? 1 : track.selected_for_dv ? 0.5 : 0.10 }),
            );
            makeInspectable(trackObject, { kind: 'track', eventId: event.event_id, vertexIndex, trackIndex });
            dynamic.add(trackObject);
          }
        }
      });

      if (event.event_id === selectedEventId) {
        for (const jet of event.jets) {
          const theta = 2 * Math.atan(Math.exp(-jet.eta));
          const length = 220;
          const jetSelected = targetKey(selectedTarget) === `jet:${event.event_id}:${jet.rank}`;
          const jetObject = line([
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(length * Math.sin(theta) * Math.cos(jet.phi), length * Math.sin(theta) * Math.sin(jet.phi), length * Math.cos(theta)),
          ], new THREE.LineBasicMaterial({ color: jetSelected ? 0xf2b134 : 0x7651a6, transparent: true, opacity: jetSelected ? 1 : selectedCutId === 'jet_selection' && jet.rank >= 4 ? 0.9 : 0.16 }));
          makeInspectable(jetObject, { kind: 'jet', eventId: event.event_id, jetRank: jet.rank });
          dynamic.add(jetObject);
        }
      }
    }
    scene.add(dynamic);
  }

  function resize(): void {
    if (!host || !renderer) return;
    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  export function resetView(): void {
    const damping = controls.enableDamping;
    controls.enableDamping = false;
    if (['rxy_gt_4_mm', 'd0_gt_2_mm', 'tracks_ge_5', 'mdv_gt_10_gev'].includes(selectedCutId)) camera.position.set(105, 78, 125);
    else camera.position.set(520, 380, 620);
    controls.target.set(0, 0, 0);
    controls.update();
    controls.enableDamping = damping;
  }

  export function setPreset(preset: '3d' | 'rz' | 'xy'): void {
    if (preset === '3d') camera.position.set(520, 380, 620);
    if (preset === 'rz') camera.position.set(680, 0, 0);
    if (preset === 'xy') camera.position.set(0, 0, 720);
    controls.target.set(0, 0, 0);
    controls.update();
  }

  function inspectAt(event: PointerEvent): InspectionTarget | null {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const priority: Record<InspectionTarget['kind'], number> = { vertex: 0, track: 1, jet: 2, layer: 3 };
    const hit = raycaster.intersectObjects(dynamic.children, true)
      .filter((candidate) => candidate.object.userData.inspectionTarget)
      .sort((a, b) => {
        const aTarget = a.object.userData.inspectionTarget as InspectionTarget;
        const bTarget = b.object.userData.inspectionTarget as InspectionTarget;
        return priority[aTarget.kind] - priority[bTarget.kind] || a.distance - b.distance;
      })[0];
    const target = hit?.object.userData.inspectionTarget as InspectionTarget | undefined;
    return target ?? null;
  }

  function pointerDown(event: PointerEvent): void { pointerStart = { x: event.clientX, y: event.clientY }; }
  function selectAt(event: PointerEvent): void {
    if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5) return;
    const target = inspectAt(event);
    if (target) onInspect(target);
  }
  function hoverAt(event: PointerEvent): void {
    const target = inspectAt(event);
    renderer.domElement.style.cursor = target ? 'pointer' : 'grab';
    onHover(target);
  }
  function clearHover(): void { onHover(null); }

  onMount(() => {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafb);
    camera = new THREE.PerspectiveCamera(42, 1, 0.1, 5000);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    host.appendChild(renderer.domElement);
    raycaster.params.Line = { threshold: 3 };
    renderer.domElement.addEventListener('pointerdown', pointerDown);
    renderer.domElement.addEventListener('pointerup', selectAt);
    renderer.domElement.addEventListener('pointermove', hoverAt);
    renderer.domElement.addEventListener('pointerleave', clearHover);
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.minDistance = 8;
    controls.maxDistance = 1800;
    observer = new ResizeObserver(resize);
    observer.observe(host);
    resetView();
    ready = true;
    rebuild();
    const animate = () => { controls.update(); renderer.render(scene, camera); frame = requestAnimationFrame(animate); };
    animate();
  });

  onDestroy(() => {
    cancelAnimationFrame(frame);
    observer?.disconnect();
    controls?.dispose();
    if (renderer) {
      renderer.domElement.removeEventListener('pointerup', selectAt);
      renderer.domElement.removeEventListener('pointerdown', pointerDown);
      renderer.domElement.removeEventListener('pointermove', hoverAt);
      renderer.domElement.removeEventListener('pointerleave', clearHover);
      renderer.dispose();
    }
    clearDynamic();
  });

  $: {
    events; geometry; selectedCutId; selectedCutKind; selectedEventId; selectedVertexIndex; showDetector; showAnalysis; showResponse; selectedTarget;
    if (ready) {
      rebuild();
      if (cameraCutId !== selectedCutId) { cameraCutId = selectedCutId; resetView(); }
    }
  }
</script>

<div class="three-host" bind:this={host} aria-label="Interactive Three.js event geometry"></div>

<style>
  .three-host { width: 100%; height: 440px; min-height: 360px; border-radius: 10px; overflow: hidden; background: #f8fafb; }
  .three-host :global(canvas) { display: block; width: 100%; height: 100%; cursor: grab; }
  .three-host :global(canvas:active) { cursor: grabbing; }
</style>
