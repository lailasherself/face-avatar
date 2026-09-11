"""Add jaw-driven dental meshes to existing review rigs without rebuilding their skin."""
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Quaternion, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import Mesh, material, export
from build_3dai_characters import Character

OUT=ROOT/'assets/3dai/rigged'
QA=ROOT/'.context/qa/teeth'
BACKUP=ROOT/'.context/before-teeth'


def profile(name,config):
    if name=='coral':
        return {'mx':0,'mz':1.79,'mw':.34,'my':-.575,'curve':-.022,'wave':0,
                'rim':[-.575+.15*(i/32)**2 for i in range(-32,33)],
                'scale':1,'angle':.37,'hinge':[0,-.02,1.91],'sideways':.085}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai'/(name+'-prepared.blend')))
    character=Character(name,config,{})
    scale=max(.40,min(1.3,max(.12,character.mw)/.34))
    return {'mx':character.mx,'mz':character.mz,'mw':character.mw,'my':character.my,
            'curve':character.curve,'wave':config.get('mouthWave',0),'rim':character.mouth_rim,
            'fit':{'fuzz':{'recess':.20,'lowerHeight':.029},
                   'clementine':{'span':.32,'upperZ':.009,'lowerZ':-.009,'upperHeight':.008,'lowerHeight':.008}}.get(name,{}),
            'scale':scale,'angle':.40,'sideways':.08*scale,
            'hinge':[character.mx,character.my+.30*scale,character.mz+.10*scale]}


def add_teeth(rig,p):
    enamel=material('Dental enamel','#f4f1df',.32)
    enamel.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.12
    objects=[]
    fit=p.get('fit',{})
    for lower in [False,True]:
        mesh=Mesh()
        count=6 if p['mw']<=.16 else 8
        span=p['mw']*fit.get('span',.72)
        step=span*2/count
        for i in range(count):
            x=p['mx']-span+step*(i+.5)
            t=(x-p['mx'])/p['mw']
            z=p['mz']+p['curve']*t*t+p['wave']*math.cos(2*math.pi*t)
            sample=(t+1)*32; j=min(63,int(sample)); f=sample-j
            front=p['rim'][j]*(1-f)+p['rim'][j+1]*f
            s=p['scale']
            # Keep roots behind the lips; only the enamel crowns enter the opening.
            center=(x,front+fit.get('recess',.12)*s,z+fit.get('lowerZ' if lower else 'upperZ',-.064 if lower else .010)*s)
            height=fit.get('lowerHeight' if lower else 'upperHeight',.037 if lower else .034)*s
            mesh.ellipsoid(center,(step*.465,.022*s,height),
                           enamel,n=16,rings=10,power=.35)
        obj=mesh.object('LowerTeeth' if lower else 'UpperTeeth',rig)
        obj['assetRole']='lower-teeth' if lower else 'upper-teeth'
        obj['dentalRigVersion']=1
        obj['toothCount']=count
        if lower:
            obj.shape_key_add(name='Basis')
            hinge=Vector(p['hinge']); rotation=Quaternion((1,0,0),p['angle'])
            for name in ['jawOpen','mouthClose','jawLeft','jawRight','jawForward']:
                key=obj.shape_key_add(name=name)
                for v in obj.data.vertices:
                    if name in ['jawOpen','mouthClose']:
                        delta=rotation@(v.co-hinge)+hinge-v.co
                        if name=='mouthClose':delta=-delta
                    elif name=='jawForward':delta=Vector((0,-.065*p['scale'],0))
                    else:delta=Vector((p['sideways']*(1 if name=='jawLeft' else -1),0,0))
                    key.data[v.index].co=v.co+delta
        objects.append(obj)
    return objects


def expression(objects,values):
    for obj in objects:
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.value=values.get(key.name,0)
    bpy.context.view_layer.update()


def main():
    QA.mkdir(parents=True,exist_ok=True); BACKUP.mkdir(parents=True,exist_ok=True)
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    requested=[n for n in sys.argv[sys.argv.index('--')+1:] if not n.startswith('--')] if '--' in sys.argv else []
    for name in [*configs,'coral']:
        if requested and name not in requested:continue
        p=profile(name,configs.get(name))
        blend=ROOT/'blender/3dai'/(name+'-rigged.blend')
        for path in [blend,OUT/(name+'.glb')]:
            backup=BACKUP/path.name
            if not backup.exists():shutil.copy2(path,backup)
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        bpy.context.preferences.filepaths.save_version=0
        rig=bpy.data.objects['AvatarRig']
        # Rerunning replaces only this pass's own dental meshes.
        for obj in list(bpy.data.objects):
            if obj.get('dentalRigVersion'):
                mesh=obj.data; mats=list(mesh.materials)
                bpy.data.objects.remove(obj,do_unlink=True)
                if mesh.users==0:bpy.data.meshes.remove(mesh)
                for mat in mats:
                    if mat.users==0:bpy.data.materials.remove(mat)
        bpy.ops.object.select_all(action='DESELECT')
        dental=add_teeth(rig,p)
        objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and
                     any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        expression(objects,{})
        export(OUT/(name+'.glb'),objects,True)
        bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        scene=bpy.context.scene;camera=scene.camera
        center=rig.matrix_world@rig.pose.bones['Head'].matrix@rig.data.bones['Head'].matrix_local.inverted()@Vector((p['mx'],p['my'],p['mz']))
        camera.location=center+Vector((.04,-4,.025))
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=max(.40,p['mw']*3.1)
        scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
        scene.cycles.samples=12
        for case,values in {'neutral':{},'jaw':{'jawOpen':1},
                            'smile':{'jawOpen':.4,'mouthSmileLeft':1,'mouthSmileRight':1}}.items():
            expression(objects,values)
            scene.render.filepath=str(QA/(name+'-'+case+'.png'))
            bpy.ops.render.render(write_still=True)
        report={'character':name,'teethPerJaw':dental[0]['toothCount'],'profile':p,
                'lowerJawChannels':['jawOpen','mouthClose','jawLeft','jawRight','jawForward']}
        (QA/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        print('TEETH',name,report['teethPerJaw'],'per jaw; saved Blender, GLB and expression renders',flush=True)


if __name__=='__main__':main()
