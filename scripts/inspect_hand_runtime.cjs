const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage();await page.goto('http://localhost:8014/cockpit.html?qa');
 const result=await page.evaluate(async()=>{
  const THREE=await import('three'),{GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
  const g=await new GLTFLoader().loadAsync('assets/3dai/refined/orbit.glb');
  const mixer=new THREE.AnimationMixer(g.scene);mixer.clipAction(g.animations.find(a=>a.name==='ArmsForward')).play();mixer.update(0);g.scene.updateMatrixWorld(true);
  const result=[];
  const {FingerRetargeter}=await import('/finger-retarget.js');
  mixer.stopAllAction();mixer.clipAction(g.animations.find(a=>a.name==='Seated')).play();mixer.update(0);
  const fingers=new FingerRetargeter(g.scene);
  mixer.stopAllAction();mixer.clipAction(g.animations.find(a=>a.name==='ArmsForward')).play();mixer.update(0);
  result.push({angles:fingers.joints.map(j=>[j.bone.name,j.bone.quaternion.angleTo(j.rest)])});
  for(let i=0;i<20;i++)fingers.update({L:{Thumb:[.7,.8,.8],Index:[1,1,1],Middle:[1,1,1],Ring:[1,1,1]}},.1);
  g.scene.updateMatrixWorld(true);
  g.scene.traverse(o=>{
   if(!o.isSkinnedMesh||!o.name.includes('Articulated'))return;
   const groups={},a=o.geometry.attributes;
   for(let i=0;i<a.position.count;i++){
    const joint=o.skeleton.bones[a.skinIndex.getX(i)].name;if(a.skinWeight.getX(i)<.99)continue;
    const v=new THREE.Vector3();o.getVertexPosition(i,v);(groups[joint]??=[]).push(v.toArray());
   }
   result.push({name:o.name,groups:Object.fromEntries(Object.entries(groups).map(([n,vs])=>[n,{count:vs.length,center:[0,1,2].map(k=>vs.reduce((s,v)=>s+v[k],0)/vs.length)}]))});
  });
  const scene=new THREE.Scene();scene.background=new THREE.Color('white');scene.add(g.scene);scene.add(new THREE.HemisphereLight(0xffffff,0x777777,3));
  const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(0,3,5);scene.add(light);
  g.scene.traverse(o=>{if(o.isMesh)o.visible=o.name.includes('Articulated');});
  const camera=new THREE.PerspectiveCamera(40,1,0.01,10);camera.position.set(.57,1.50,1.7);camera.lookAt(.57,1.50,.7);
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(800,800);document.body.replaceChildren(renderer.domElement);renderer.render(scene,camera);
  window.doubleHands=()=>{g.scene.traverse(o=>{if(o.isMesh){o.material.side=THREE.DoubleSide;o.material.needsUpdate=true;}});renderer.render(scene,camera);};
  return result;
 });console.log(JSON.stringify(result,null,2));await page.screenshot({path:'.context/qa/refinement/hand-frontside.png'});await page.evaluate(()=>doubleHands());await page.screenshot({path:'.context/qa/refinement/hand-doubleside.png'});await browser.close();
})().catch(console.error);
