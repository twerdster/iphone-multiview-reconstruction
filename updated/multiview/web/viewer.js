/* Dependency-free WebGL point-cloud viewer. Geometry comes from reconstruction. */
'use strict';
class PointViewer {
  constructor(canvas) {
    this.canvas=canvas; this.gl=canvas.getContext('webgl',{antialias:true,preserveDrawingBuffer:true});
    if(!this.gl) throw new Error('This browser does not provide WebGL');
    const gl=this.gl;
    const vertex=`attribute vec3 position; attribute vec3 color; uniform float yaw; uniform float pitch; uniform float distance; uniform float aspect; uniform float pointSize; varying vec3 rgb;
      void main(){float cy=cos(yaw),sy=sin(yaw),cx=cos(pitch),sx=sin(pitch);vec3 p=vec3(cy*position.x+sy*position.z,position.y,-sy*position.x+cy*position.z);p=vec3(p.x,cx*p.y-sx*p.z,sx*p.y+cx*p.z);float z=p.z+distance;gl_Position=vec4(p.x*2.2/aspect,p.y*2.2,z*.999-.02,z);gl_PointSize=clamp(pointSize*2.8/max(z,.1),1.,8.);rgb=color;}`;
    const fragment=`precision mediump float; varying vec3 rgb; void main(){if(length(gl_PointCoord-vec2(.5))>.5)discard;gl_FragColor=vec4(rgb,1.);}`;
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    this.program=gl.createProgram();gl.attachShader(this.program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program));
    this.buffer=gl.createBuffer();this.count=0;this.pointSize=2;this.auto=false;this.pointers=new Map();this.reset();
    canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,[e.clientX,e.clientY]);this.auto=false;});
    canvas.addEventListener('pointermove',e=>{const old=this.pointers.get(e.pointerId);if(!old)return;const now=[e.clientX,e.clientY];if(this.pointers.size===1){this.yaw+=(now[0]-old[0])*.008;this.pitch=Math.max(-1.5,Math.min(1.5,this.pitch+(now[1]-old[1])*.008));}else{const other=[...this.pointers.entries()].find(([id])=>id!==e.pointerId)[1];const previous=Math.hypot(old[0]-other[0],old[1]-other[1]);const current=Math.hypot(now[0]-other[0],now[1]-other[1]);if(current>0)this.distance=Math.max(.7,Math.min(12,this.distance*previous/current));}this.pointers.set(e.pointerId,now);});
    ['pointerup','pointercancel','lostpointercapture'].forEach(name=>canvas.addEventListener(name,e=>this.pointers.delete(e.pointerId)));
    canvas.addEventListener('wheel',e=>{e.preventDefault();this.distance=Math.max(.7,Math.min(12,this.distance*Math.exp(e.deltaY*.001)));},{passive:false});
    this.previous=performance.now();const render=t=>{const dt=Math.min(.05,(t-this.previous)/1000);this.previous=t;if(this.auto)this.yaw+=dt*.16;this.render();requestAnimationFrame(render);};requestAnimationFrame(render);
  }
  reset(){this.yaw=0;this.pitch=0;this.distance=2.8;}
  load(data){
    if(!data.points.length)throw new Error('The reconstruction contains no points');
    // Start in the orientation of an estimated camera; CV camera y points down.
    const orientation=data.cameras?.[Math.floor(data.cameras.length/2)]?.rotation_world_from_camera;
    const points=orientation?data.points.map(p=>[0,1,2].map(i=>p.reduce((s,v,j)=>s+v*orientation[j][i],0))):data.points;
    const bounds=[0,1,2].map(axis=>{const values=points.map(p=>p[axis]).sort((a,b)=>a-b);return [values[Math.floor(values.length*.01)],values[Math.floor(values.length*.99)]];});
    const center=bounds.map(b=>(b[0]+b[1])/2), scale=Math.max(...bounds.map(b=>b[1]-b[0]))||1;
    const vertices=new Float32Array(data.points.length*6);
    points.forEach((point,i)=>{for(let axis=0;axis<3;axis++){vertices[i*6+axis]=(point[axis]-center[axis])/scale*2*(axis===1?-1:1);vertices[i*6+axis+3]=data.colors[i][axis]/255;}});
    this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.buffer);this.gl.bufferData(this.gl.ARRAY_BUFFER,vertices,this.gl.STATIC_DRAW);this.count=data.points.length;this.reset();
  }
  render(){
    const gl=this.gl,c=this.canvas,dpr=Math.min(window.devicePixelRatio||1,2),width=Math.round(c.clientWidth*dpr),height=Math.round(c.clientHeight*dpr);
    if(c.width!==width||c.height!==height){c.width=width;c.height=height;}gl.viewport(0,0,width,height);gl.clearColor(.035,.065,.10,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);if(!this.count)return;
    gl.useProgram(this.program);gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
    [['position',0],['color',12]].forEach(([name,offset])=>{const a=gl.getAttribLocation(this.program,name);gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,24,offset);});
    Object.entries({yaw:this.yaw,pitch:this.pitch,distance:this.distance,aspect:width/height,pointSize:this.pointSize*dpr}).forEach(([name,value])=>gl.uniform1f(gl.getUniformLocation(this.program,name),value));
    gl.drawArrays(gl.POINTS,0,this.count);
  }
}
window.PointViewer=PointViewer;
