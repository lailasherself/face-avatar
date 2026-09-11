"""Smooth facial displacement fields without changing base topology or body rigs."""
import json
from pathlib import Path
import shutil
import sys
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import export
from post_skin_correctives import export_space


def refine(body):
    keys=body.data.shape_keys.key_blocks
    size=len(body.data.vertices)
    base=np.empty(size*3);keys['Basis'].data.foreach_get('co',base);base=base.reshape(-1,3)
    edges=np.array([e.vertices[:] for e in body.data.edges],dtype=int)
    degree=np.bincount(edges.ravel(),minlength=size)[:,None]
    body.data.calc_loop_triangles()
    triangles=np.array([t.vertices[:] for t in body.data.loop_triangles],dtype=int)
    normals=np.cross(base[triangles[:,1]]-base[triangles[:,0]],base[triangles[:,2]]-base[triangles[:,0]])
    lengths=np.maximum(.002,np.linalg.norm(base[edges[:,1]]-base[edges[:,0]],axis=1))
    def defects(delta):
        p=base+delta
        n=np.cross(p[triangles[:,1]]-p[triangles[:,0]],p[triangles[:,2]]-p[triangles[:,0]])
        flipped=int(np.count_nonzero(np.sum(normals*n,axis=1)<-1e-16))
        stretched=int(np.count_nonzero(np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)>2*lengths))
        return flipped*4+stretched
    for key in keys:
        if not key.name.startswith(('mouth','jaw')) or key.name=='mouthClose':continue
        coords=np.empty(size*3);key.data.foreach_get('co',coords)
        delta=coords.reshape(-1,3)-base;original=delta.copy()
        support=np.linalg.norm(delta,axis=1)>1e-7
        if not support.any():continue
        # Diffuse the displacement, not the character's textured neutral surface.
        # Mouth cut edges remain disconnected, so upper/lower lips cannot weld.
        for _ in range(16):
            total=np.zeros_like(delta)
            np.add.at(total,edges[:,0],delta[edges[:,1]])
            np.add.at(total,edges[:,1],delta[edges[:,0]])
            delta=.5*delta+.5*total/np.maximum(1,degree)
            delta[~support]=0
        best=original;score=defects(original)
        for amount in [.25,.5,.75,1]:
            candidate=original*(1-amount)+delta*amount;quality=defects(candidate)
            if quality<score:best=candidate;score=quality
        key.data.foreach_set('co',(base+best).ravel())
    opened=np.empty(size*3);keys['jawOpen'].data.foreach_get('co',opened)
    keys['mouthClose'].data.foreach_set('co',(2*base-opened.reshape(-1,3)).ravel())
    body['mouthRefinementVersion']=2


def main():
    backup=ROOT/'.context/before-mouth-cleanup';backup.mkdir(parents=True,exist_ok=True)
    requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
        name=entry['id']
        if requested and name not in requested:continue
        blend=ROOT/'blender/3dai/refined'/f'{name}-rigged.blend';glb=ROOT/entry['url']
        for path in [blend,glb]:
            if not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
        bpy.ops.wm.open_mainfile(filepath=str(backup/blend.name));bpy.context.preferences.filepaths.save_version=0
        rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody'];refine(body)
        objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        drivers=[]
        for obj in objects:
            if obj.type!='MESH' or not obj.data.shape_keys:continue
            if obj.data.shape_keys.animation_data:
                for driver in obj.data.shape_keys.animation_data.drivers:drivers.append((driver,driver.mute));driver.mute=True
            for key in obj.data.shape_keys.key_blocks:key.value=0
        export_space(body,body['correctiveSamples'],True);export(glb,objects,True,morph_normals=True)
        export_space(body,body['correctiveSamples'],False)
        for driver,mute in drivers:driver.mute=mute
        bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('MOUTH REFINED',name,flush=True)


if __name__=='__main__':main()
