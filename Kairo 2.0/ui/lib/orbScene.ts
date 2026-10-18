import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export interface OrbSceneApi {
  rotateBy(theta: number, phi: number): void;
  zoomBy(factor: number): void;
  zoomIn(): void;
  zoomOut(): void;
  resetView(): void;
  setActivity(state: string, level: number): void;
  dispose(): void;
}

// Original geometry: a luminous geodesic core and fine spherical signal field.
// Motion is a visualization of real runtime state, never a simulated conversation.
export function createOrbScene(container: HTMLElement): OrbSceneApi {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02050a);
  const camera = new THREE.PerspectiveCamera(42, 1, .1, 60);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  container.appendChild(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.minDistance = 4.2;
  controls.maxDistance = 30;
  const globe = new THREE.Group();
  scene.add(globe);
  const shellMaterial = new THREE.LineBasicMaterial({ color: 0x2688dc, transparent: true, opacity: .28 });
  const shell = new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.84, 3)), shellMaterial);
  globe.add(shell);
  const innerMaterial = new THREE.LineBasicMaterial({ color: 0x5abfff, transparent: true, opacity: .18 });
  const inner = new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.58, 2)), innerMaterial);
  globe.add(inner);
  const positions: number[] = [];
  const count = 3600;
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - 2 * i / (count - 1), radius = Math.sqrt(1 - y * y), angle = i * golden;
    positions.push(1.87 * radius * Math.cos(angle), 1.87 * y, 1.87 * radius * Math.sin(angle));
  }
  const particles = new THREE.BufferGeometry();
  particles.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  const pointMaterial = new THREE.PointsMaterial({ color: 0x83d2ff, size: .012, transparent: true, opacity: .64, blending: THREE.AdditiveBlending });
  globe.add(new THREE.Points(particles, pointMaterial));
  const ringMaterial = new THREE.LineBasicMaterial({ color: 0x408ec9, transparent: true, opacity: .27 });
  for (const radius of [2.12, 2.17]) {
    const points = Array.from({ length: 257 }, (_, i) => {
      const a = i / 256 * Math.PI * 2;
      return new THREE.Vector3(radius * Math.cos(a), 0, radius * Math.sin(a));
    });
    const ring = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), ringMaterial);
    ring.rotation.set(.32, 0, -.26);
    globe.add(ring);
  }
  const coreMaterial = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { strength: { value: .28 }, tint: { value: new THREE.Color(0x329aff) } },
    vertexShader: `varying vec3 n; varying vec3 v; void main(){vec4 p=modelViewMatrix*vec4(position,1.);n=normalize(normalMatrix*normal);v=normalize(-p.xyz);gl_Position=projectionMatrix*p;}`,
    fragmentShader: `varying vec3 n; varying vec3 v; uniform float strength; uniform vec3 tint; void main(){float rim=pow(1.-abs(dot(normalize(n),normalize(v))),3.);gl_FragColor=vec4(tint,(.035+rim*.7)*strength);}`,
  });
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(1.78, 64, 48), coreMaterial));
  let state = "offline", level = 0, lastAudio = 0, frame = 0, previous = performance.now();
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  function resetView() { camera.position.set(0, .15, 7 * Math.max(1, container.clientHeight / Math.max(1, container.clientWidth))); controls.target.set(0, 0, 0); controls.update(); }
  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    camera.aspect = w / Math.max(h, 1); camera.updateProjectionMatrix(); renderer.setSize(w, h); resetView();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(container); resize(); resetView();
  function render(now: number) {
    frame = requestAnimationFrame(render);
    const dt = Math.min((now - previous) / 1000, .1); previous = now;
    if (document.hidden) return;
    const active = ["listening", "speaking", "thinking", "acting", "permission"].includes(state);
    const audio = now - lastAudio < 500 ? level : 0;
    const strength = state === "offline" ? .18 : active ? .72 : .48;
    const target = state === "permission" ? 0xc1d6ff : state === "error" ? 0xe77796 : state === "acting" ? 0x62e0f4 : 0x329aff;
    coreMaterial.uniforms.tint.value.setHex(target);
    coreMaterial.uniforms.strength.value = strength + audio * .5;
    shellMaterial.opacity = strength * .48;
    pointMaterial.opacity = .22 + strength * .6;
    innerMaterial.opacity = state === "thinking" ? .5 : .16;
    ringMaterial.opacity = state === "acting" ? .7 : .2;
    if (!reduced.matches) {
      // Standby is still. Active motion and amplitude are driven by server events.
      if (active) globe.rotation.y += dt * (state === "thinking" ? .14 : .035);
      const scale = 1 + audio * .035;
      globe.scale.lerp(new THREE.Vector3(scale, scale, scale), .15);
    }
    controls.update(); renderer.render(scene, camera);
  }
  frame = requestAnimationFrame(render);
  return {
    rotateBy(theta, phi) { globe.rotation.y += theta; globe.rotation.x += phi; },
    zoomBy(factor) { camera.position.multiplyScalar(factor).clampLength(4.2, 30); },
    zoomIn() { camera.position.multiplyScalar(.9).clampLength(4.2, 30); },
    zoomOut() { camera.position.multiplyScalar(1.1).clampLength(4.2, 30); }, resetView,
    setActivity(next, amplitude) { state = next; level = Math.max(0, Math.min(1, amplitude)); lastAudio = performance.now(); },
    dispose() {
      cancelAnimationFrame(frame); observer.disconnect(); controls.dispose();
      const materials = new Set<THREE.Material>();
      globe.traverse(object => { const mesh = object as THREE.Mesh; mesh.geometry?.dispose(); if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(m => materials.add(m)); });
      materials.forEach(m => m.dispose()); renderer.dispose(); renderer.domElement.remove();
    },
  };
}
