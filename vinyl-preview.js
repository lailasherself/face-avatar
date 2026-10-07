import * as THREE from 'three';

// The original print stays intact; only its white dome reveals the live TV feed.
export class VinylPreview {
  constructor(){
    this.target=new THREE.WebGLRenderTarget(1280,720,{type:THREE.HalfFloatType});
    this.scene=new THREE.Scene();this.camera=new THREE.Camera();this.ready=false;
    const artwork=new THREE.TextureLoader().load('assets/references/ufo1-vinyl.jpg',()=>{this.ready=true;});
    artwork.colorSpace=THREE.SRGBColorSpace;
    this.material=new THREE.ShaderMaterial({
      uniforms:{artwork:{value:artwork},feed:{value:this.target.texture},aspect:{value:1},closeUp:{value:false}},
      depthTest:false,depthWrite:false,
      vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}',
      fragmentShader:`
        uniform sampler2D artwork;
        uniform sampler2D feed;
        uniform float aspect;
        uniform bool closeUp;
        varying vec2 vUv;
        void main(){
          vec2 uv=vUv;
          float imageAspect=1908.0/1312.0;
          if(closeUp){
            vec2 pixel=vec2(590.0,792.0)+(vec2(vUv.x,1.0-vUv.y)-.5)*vec2(664.0*aspect,664.0);
            uv=vec2(pixel.x/1908.0,1.0-pixel.y/1312.0);
          }else{
            if(aspect>imageAspect)uv.x=(uv.x-.5)*aspect/imageAspect+.5;
            else uv.y=(uv.y-.5)*imageAspect/aspect+.5;
          }
          if(any(lessThan(uv,vec2(0.0)))||any(greaterThan(uv,vec2(1.0)))){
            gl_FragColor=vec4(.005,.009,.014,1.0);return;
          }
          vec4 printColor=texture2D(artwork,uv);
          vec2 pixel=vec2(uv.x*1908.0,(1.0-uv.y)*1312.0);
          vec2 tv=(pixel-vec2(370.0,535.0))/vec2(440.0,247.5);
          float dome=step(310.0,pixel.x)*step(pixel.x,880.0)*step(540.0,pixel.y)*step(pixel.y,805.0);
          float white=smoothstep(.8,.97,min(printColor.r,min(printColor.g,printColor.b)))*dome;
          vec4 alien=texture2D(feed,vec2(tv.x,1.0-tv.y));
          #if defined(TONE_MAPPING)
            alien.rgb=toneMapping(alien.rgb);
          #endif
          gl_FragColor=mix(printColor,alien,white);
          #include <colorspace_fragment>
        }`,
    });
    const overlay=new THREE.Mesh(new THREE.PlaneGeometry(2,2),this.material);
    overlay.frustumCulled=false;this.scene.add(overlay);
  }
  render(renderer,scene,camera,closeUp=false){
    const previous=renderer.getRenderTarget();
    renderer.setRenderTarget(this.target);renderer.render(scene,camera);
    renderer.setRenderTarget(previous);
    const size=renderer.getSize(new THREE.Vector2());
    this.material.uniforms.aspect.value=size.x/size.y;
    this.material.uniforms.closeUp.value=closeUp;
    renderer.render(this.scene,this.camera);
  }
}
