"""Live-MCP mouth topology repair for the isolated Glass working file."""
import math
import bpy
from mathutils import Vector
from build_reference_glass import C


def rebuild_front(object_name='Face',config=C,transform=None,cavity_material='Glass cavity',local_travel=.06,outer_travel=.035):
    ob=bpy.context.scene.objects[object_name]
    assert not ob.get('radialMouthPatch'),'Mouth patch already applied'
    hw,hd,hh=config['head'];hz=config['hz'];mw,mz,mh=config['mouth'];power=config['power']
    keys=ob.data.shape_keys.key_blocks;basis=keys['Basis']
    inner={k.name:[k.data[i].co-basis.data[i].co for i in range(80)] for k in keys}
    for col in range(80):
        a=2*math.pi*col/80;dx=hw*math.cos(a);dz=hh*math.sin(a)
        lo,hi=0,4
        for _ in range(40):
            t=(lo+hi)/2
            if abs(t*dx/hw)**(2/power)+abs((mz+t*dz)/hh)**(2/power)>1:hi=t
            else:lo=t
        end=Vector((lo*dx,0,mz+lo*dz))
        start=Vector((mw*math.cos(a),0,mz+mh*math.sin(a)))
        lower=max(0,-math.sin(a))**.7
        for row in range(38):
            u=row/37;i=row*80+col;p=start.lerp(end,u)
            p.y=-hd*max(0,1-abs(p.x/hw)**(2/power)-abs(p.z/hh)**(2/power))**(power/2)
            p.z+=hz
            for key in keys:
                d=inner[key.name][col]*(1-u)
                if key.name=='jawOpen':d=Vector((0,-.005*lower*(1-u),-(local_travel*(1-u)+outer_travel)*lower))
                elif key.name=='mouthClose':d=Vector((0,0,mh*lower*(1-u)))
                elif key.name.startswith('brow'):
                    ex,ez,_,_,rz=config['eyes']
                    w=math.exp(-((abs(p.x)-ex)/.22)**2-((p.z-hz-ez-rz*.9)/.16)**2)
                    side=min(1,max(0,(p.x+.07)/.14))
                    if key.name.endswith('Right'):side=1-side
                    elif not key.name.endswith('Left'):side=1
                    d=Vector((0,0,w*(.045 if 'Up' in key.name else -.035)*side))
                key.data[i].co=transform(p+d,i) if transform else p+d
        for row in range(22):
            u=row/21;i=3040+row*80+col
            p=Vector((end.x*math.cos(u*math.pi/2),hd*math.sin(u*math.pi/2),end.z*math.cos(u*math.pi/2)+hz))
            angle=math.atan2((p.z-hz-mz)/hh,p.x/hw)
            lower_back=max(0,-math.sin(angle))**.7
            for key in keys:
                value=p+Vector((0,0,-outer_travel*lower_back if key.name=='jawOpen' else 0))
                key.data[i].co=transform(value,i) if transform else value
    for v,k in zip(ob.data.vertices,basis.data):v.co=k.co
    ob.data.update();ob['radialMouthPatch']=True
    # Keep the far oral wall stationary; only the entry follows the lower lip.
    cavity=sorted({i for p in ob.data.polygons if ob.data.materials[p.material_index].name==cavity_material for i in p.vertices})
    for j,i in enumerate(cavity):
        a=2*math.pi*(j%64)/64;lower=max(0,-math.sin(a))**.7
        d=Vector((0,-.005*lower,-(local_travel+outer_travel)*lower*(1-(j//64)/7))) if j<512 else Vector()
        keys['jawOpen'].data[i].co=basis.data[i].co+d
    lip=list(range(5600,6120))
    for j,i in enumerate(lip):
        lower=max(0,-math.sin(2*math.pi*(j//8)/64))**.7
        keys['jawOpen'].data[i].co=basis.data[i].co+Vector((0,-.005*lower,-(local_travel+outer_travel)*lower))
    teeth=bpy.context.scene.objects['Teeth'];dental=teeth.data.shape_keys.key_blocks
    for i,p in enumerate(dental['jawOpen'].data):
        rest=dental['Basis'].data[i].co
        if p.co.z<rest.z-.01:p.co=rest+Vector((0,-.005,-.062))
    bpy.context.view_layer.update()
    return {'frontVertices':3040,'mouthCenteredRadialTopology':True,'cavityVertices':len(cavity),'lipVertices':len(lip)}


def save():
    import json
    from build_reference_glass import ROOT,reset,standing,validate,validate_export
    rig=bpy.context.scene.objects['AvatarRig']
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent==rig]
    report=validate(rig,objects);reset(rig,objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig,*objects]:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    path=ROOT/'assets/reference-characters/glass-review.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_extras=True,export_attributes=True,export_morph=True,export_morph_normal=True)
    report['exportValidation']=validate_export(path)
    (ROOT/'.context/qa/reference-characters/glass-validation.json').write_text(json.dumps(report,indent=2))
    standing(rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/reference-characters/glass-review.blend'))
    print(report)
