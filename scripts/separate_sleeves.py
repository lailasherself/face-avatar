"""Separate fused sleeve/torso surfaces and close their hidden seam boundaries."""
import bpy
import bmesh
from build_avatar_fleet import material


def separate_sleeves(body,rig,name,config):
    bm=bmesh.new();bm.from_mesh(body.data)
    deform=bm.verts.layers.deform.active;piece=bm.faces.layers.int.new('Sleeve piece')
    groups={side:{body.vertex_groups[n+'.'+side].index for n in ['UpperArm','Forearm','Hand']} for side in ['L','R']}
    all_arms=groups['L']|groups['R']
    width,height,top,slope={'clementine':(.27,1.78,1.83,.15),'sprout':(.29,1.49,1.54,.15)}[name]
    for side,sign in [('L',1),('R',-1)]:
        local=[f for f in bm.faces if f.calc_center_median().z<top+.04 and
               abs(sign*f.calc_center_median().x-width-max(0,height-f.calc_center_median().z)*slope)<.10]
        geometry=[*local,*{e for f in local for e in f.edges},*{v for f in local for v in f.verts}]
        bmesh.ops.bisect_plane(bm,geom=geometry,dist=.000001,plane_co=(sign*width,0,height),
                              plane_no=(sign,0,slope),clear_inner=False,clear_outer=False)
    for face in bm.faces:
        totals={side:sum(sum(v[deform].get(g,0) for g in indices) for v in face.verts)/len(face.verts) for side,indices in groups.items()}
        side=max(totals,key=totals.get)
        x,y,z=face.calc_center_median()
        # The jacket's front panels lie close to the arms. Heat weights alone
        # classify those panels as sleeves; keep the reviewed torso silhouette.
        sleeve=abs(x)>width+max(0,height-z)*slope+.000001 and z<top and totals[side]>.05
        face[piece]=(1 if side=='L' else 2) if sleeve else 0
    seams=[e for e in bm.edges if len(e.link_faces)==2 and e.link_faces[0][piece]!=e.link_faces[1][piece]]
    def edge_key(edge):return tuple(sorted(tuple(round(c,6) for c in v.co) for v in edge.verts))
    seam_keys={edge_key(e) for e in seams}
    bmesh.ops.split_edges(bm,edges=seams)
    for vertex in bm.verts:
        classes={f[piece] for f in vertex.link_faces}
        if not classes:continue
        assert len(classes)==1,(name,'unseparated sleeve junction',classes)
        part=classes.pop();weights=vertex[deform]
        allowed=groups['L' if part==1 else 'R'] if part else set(weights.keys())-all_arms
        total=sum(weights.get(g,0) for g in allowed)
        if total<1e-8:
            weights.clear();weights[body.vertex_groups['Chest' if not part else 'UpperArm.'+('L' if part==1 else 'R')].index]=1
            continue
        retained={g:weights.get(g,0)/total for g in allowed if weights.get(g,0)>1e-8}
        weights.clear()
        for group,weight in retained.items():weights[group]=weight
    boundary=[e for e in bm.edges if e.is_boundary and edge_key(e) in seam_keys]
    caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
    colors={'clementine':'#d86927','coral':'#c47f90','sprout':'#d98722','orbit':'#b89ac8',
            'pearl':'#d9b7c0','juno':'#ed9b53','fuzz':'#cba7c1','atl':'#9abb8b'}
    cap_material=material(name+' inner sleeve',colors[name],.65)
    body.data.materials.append(cap_material);index=len(body.data.materials)-1
    for face in caps:face.material_index=index;face.smooth=True
    if caps:bmesh.ops.triangulate(bm,faces=caps)
    bm.normal_update();bm.to_mesh(body.data);bm.free();body.data.update()
    body['sleeveSeamsClosed']=len(caps)
    print('SLEEVE_SEAMS',name,len(seams),'split edges',len(caps),'closed boundaries',flush=True)
