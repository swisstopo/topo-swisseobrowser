/* What the page's 3D objects (3D Tiles, section 2b2) use of three.js, with its glTF and Draco loaders: one tree-shaken
   bundle. A class the page starts to use has to be added here. */
export {
  Box3, BufferAttribute, BufferGeometry, Camera, DirectionalLight, DoubleSide, Frustum, Group, HemisphereLight,
  InstancedMesh, LoadingManager, Matrix4, Mesh, MeshLambertMaterial, PCFShadowMap, Scene, ShadowMaterial, TextureLoader,
  Vector3, WebGLRenderer
} from "three";
export { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
export { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
