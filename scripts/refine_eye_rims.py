"""Fair the source-to-lid boundary while preserving facial target deltas."""
import numpy as np
import bmesh


def refine_eye_rims(body,face):
    surfaces=face.get('eyelidSurfaces',[])
    if not surfaces:return
    bm=bmesh.new();bm.from_mesh(body.data);selected=set()
    for polygon in bm.faces:
        p=polygon.calc_center_median()
        for surface in surfaces:
            x,z,y=surface['center'];rx,rz,ry=surface['radii'];y=-y
            radial=((p.x-x)/rx)**2+((p.z-z)/rz)**2
            if .6<radial<1.9 and p.y<y+ry*.3:
                selected.update(edge for edge in polygon.edges if edge.calc_length()>min(rx,rz)*.12)
    if selected:bmesh.ops.subdivide_edges(bm,edges=list(selected),cuts=1,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.to_mesh(body.data);bm.free();body.data.update()
    rest=np.array([v.co[:] for v in body.data.vertices]);points=rest.copy();mask=np.zeros(len(rest))
    for surface in surfaces:
        x,z,y=surface['center'];rx,rz,ry=surface['radii'];y=-y
        radial=((rest[:,0]-x)/rx)**2+((rest[:,2]-z)/rz)**2
        ring=np.clip((radial-.78)/.25,0,1)*np.clip((1.65-radial)/.35,0,1)
        ring*=rest[:,1]<y+ry*.3
        mask=np.maximum(mask,ring)
    edges=np.array([e.vertices[:] for e in body.data.edges]);degree=np.bincount(edges.ravel(),minlength=len(rest))
    for _ in range(16):
        total=np.zeros_like(points)
        np.add.at(total,edges[:,0],points[edges[:,1]]);np.add.at(total,edges[:,1],points[edges[:,0]])
        points+=(total/np.maximum(1,degree[:,None])-points)*mask[:,None]*.35
    delta=points-rest;distance=np.linalg.norm(delta,axis=1)
    delta*=np.minimum(1,.018/np.maximum(distance,1e-8))[:,None]
    for key in body.data.shape_keys.key_blocks:
        values=np.array([p.co[:] for p in key.data])+delta
        key.data.foreach_set('co',values.astype(np.float32).ravel())
    body.data.vertices.foreach_set('co',(rest+delta).astype(np.float32).ravel());body.data.update()
