"""Reference-traced crown and volumetric leaf/vine attachments, built in live Blender."""
import bpy
import math
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree
from complete_clay_likeness import mesh,plain_material,smooth
from complete_cosmic_likeness import loop,inside,tube
import complete_kudzu_likeness as k

CROWN=[(382,298),(363,266),(323,254),(279,255),(272,239),(294,226),(251,213),(223,191),(215,175),(232,164),(267,161),(303,177),(283,146),(278,119),(290,108),(318,120),(303,95),(300,82),(311,75),(326,79),(338,65),(353,64),(365,68),(371,82),(390,82),(400,94),(392,113),(410,109),(425,118),(426,137),(414,161),(405,182),(430,164),(451,155),(473,156),(490,166),(488,180),(466,196),(489,192),(492,204),(480,219),(451,236),(416,250),(404,274),(393,296)]
LEAF=[(0,0),(-.25,.10),(-.46,.32),(-.45,.52),(-.28,.48),(-.38,.69),(-.26,.86),(-.10,.77),(0,1),(.12,.78),(.28,.86),(.38,.68),(.27,.48),(.46,.51),(.44,.30),(.25,.10)]


def material(name):
    m=bpy.data.materials.get('Kudzu '+name)
    if m:return m
    m=plain_material('Kudzu '+name,{'Crown Leaf':(.002,.025,.002),'Body Leaf':(.015,.045,.005),'Leaf Vein':(.008,.034,.003),'Vine':(.024,.09,.004)}[name],.68);m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.18;return m


def leaf(name,outline,project,main,branches,kind='Crown Leaf',vein_radius=.004):
    boundary=loop(outline,3);coords=list(boundary);n=len(coords);edges=[(i,(i+1)%n) for i in range(n)]
    lo=Vector((min(p.x for p in coords),min(p.y for p in coords)));hi=Vector((max(p.x for p in coords),max(p.y for p in coords)))
    for i in range(1,16):
        for j in range(1,18):
            p=Vector((lo.x+(hi.x-lo.x)*i/16,lo.y+(hi.y-lo.y)*j/18))
            if inside(p,boundary):coords.append(p)
    dv,de,df,*_=delaunay_2d_cdt(coords,edges,[],0,1e-7);fs=[f for f in df if inside(sum((dv[i] for i in f),Vector((0,0)))/len(f),boundary)]
    o=mesh(name,[project(p) for p in dv],fs,material(kind));bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Living leaf thickness','SOLIDIFY');mod.thickness=.006;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
    pieces=[o]
    for i,path in enumerate([main,*branches]):
        if i and not all(inside(Vector(p),boundary) for p in path):continue
        points=[project(Vector(p))+Vector((0,-.006,0)) for p in path];r=vein_radius if i==0 else vein_radius*.65
        pieces.append(tube(name+' Vein '+str(i),points,[r]*len(points),material('Leaf Vein'),rings=24,sides=8))
    return join(name,pieces)


def join(name,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;return o


def crown():
    def project(p):
        v=k.point(p.x,p.y);t=(p.y-65)/233;v.y=-.17-.10*t-.035*math.sin(math.pi*t);return v
    main=[(383,291),(374,247),(366,204),(358,158),(351,113),(344,73)]
    branches=[[(379,268),(347,232),(284,246)],[(371,240),(322,201),(229,177)],[(364,205),(334,167),(287,122)],[(355,154),(329,121),(310,84)],[(354,137),(376,117),(390,91)],[(361,188),(392,157),(416,124)],[(371,231),(413,193),(478,168)],[(378,264),(414,235),(481,205)]]
    parts=[leaf('Kudzu Crown Main Leaf',CROWN,project,main,branches,vein_radius=.0045)]
    for i,(px,py,scale,angle) in enumerate([(173,355,.19,-.75),(200,315,.21,-.4),(242,290,.20,.15),(482,283,.19,.65),(533,330,.20,.8),(157,491,.15,-.75)]):
        anchor=k.point(px,py);anchor.y=k.depth((anchor.x,anchor.z))-.025;parts.append(small_leaf('Kudzu Crown Side '+str(i),anchor,scale,angle,'Crown Leaf'))
    return join('Kudzu Crown Foliage',parts)


def small_leaf(name,anchor,size,angle,kind='Body Leaf'):
    def project(p):
        x=p.x*size;z=p.y*size;v=Vector((x*math.cos(angle)-z*math.sin(angle),-.025*math.sin(math.pi*p.y)*(1-abs(p.x)),x*math.sin(angle)+z*math.cos(angle)));return Vector(anchor)+v
    main=[(0,0),(0,.3),(0,.65),(0,.98)];branches=[[(0,.18),(-.2,.23),(-.40,.40)],[(0,.18),(.2,.23),(.40,.40)],[(0,.45),(-.18,.59),(-.27,.79)],[(0,.45),(.18,.59),(.27,.79)]]
    return leaf(name,LEAF,project,main,branches,kind,vein_radius=.0025)


def brows():
    for side,points in [('R',[(199,367),(211,337),(238,321),(282,315),(325,315),(350,326),(355,347),(326,342),(286,343),(243,348),(214,363)]),('L',[(411,341),(416,320),(448,310),(489,310),(526,319),(552,339),(560,356),(530,345),(490,341),(452,341),(424,348)])]:
        def project(p):
            v=k.point(p.x,p.y);v.y=k.depth((v.x,v.z))-.025;return v
        lo=min(x for x,y in points);hi=max(x for x,y in points);mid=sum(y for x,y in points)/len(points)
        main=[(lo+8,mid+8),((lo+hi)/2,mid),(hi-8,mid)]
        branches=[[(x,mid+3),(x+9,mid-2),(x+18,mid-9)] for x in range(int(lo)+10,int(hi)-20,13)]
        o=leaf('Kudzu Leaf Brow '+side,points,project,main,branches,vein_radius=.003);base=o.shape_key_add(name='Basis',from_mix=False)
        for name,delta in [('browDown'+('Left' if side=='L' else 'Right'),-.022),('browOuterUp'+('Left' if side=='L' else 'Right'),.029),('browInnerUp',.02)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,delta))


def body_foliage():
    body=k.obj('Kudzu Body');rig=k.obj('Kudzu AvatarRig');body.data.calc_loop_triangles();tri=[t.vertices[:] for t in body.data.loop_triangles];tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],tri,all_triangles=True)
    def nearest(p):return tree.find_nearest(Vector(p))
    def weights(p):
        co,normal,index,dist=nearest(p);ids=tri[index];a,b,c=[body.data.vertices[i].co for i in ids];v0=b-a;v1=c-a;v2=co-a;den=v0.dot(v0)*v1.dot(v1)-v0.dot(v1)**2
        v=(v1.dot(v1)*v2.dot(v0)-v0.dot(v1)*v2.dot(v1))/den;w=(v0.dot(v0)*v2.dot(v1)-v0.dot(v1)*v2.dot(v0))/den;f=[max(0,1-v-w),max(0,v),max(0,w)];out={}
        for i,t in zip(ids,f):
            for g in body.data.vertices[i].groups:n=body.vertex_groups[g.group].name;out[n]=out.get(n,0)+g.weight*t
        pairs=sorted(out.items(),key=lambda p:-p[1])[:4];total=sum(v for n,v in pairs);return [(n,v/total) for n,v in pairs]
    def bind(o,anchor=None):
        gs={b.name:o.vertex_groups.new(name=b.name) for b in rig.data.bones};fixed=weights(anchor) if anchor is not None else None
        for v in o.data.vertices:
            for name,value in fixed or weights(v.co):gs[name].add([v.index],value,'REPLACE')
        o.parent=rig;m=o.modifiers.new('Bound living foliage','ARMATURE');m.object=rig
    vines=[]
    for side,(path,radii) in {s:(p,k.ARM_RADII[s]) for s,p in k.ARMS.items()}.items():
        for phase_index,phase in enumerate([0,math.pi]):
            points=[]
            for i in range(70):
                t=i/69;u=t*2;j=min(1,int(u));f=u-j;a,b=Vector(path[j]),Vector(path[j+1]);center=a.lerp(b,f);radius=radii[j]*(1-f)+radii[j+1]*f;phi=t*math.tau*1.7+phase;p=center+Vector((radius*math.cos(phi),-radius*math.sin(phi),0));co,no,_,_=nearest(p);points.append(co+no*.013)
            o=tube('Kudzu Arm Vine '+side+' '+str(phase_index),points,[.012]*len(points),material('Vine'),rings=130,sides=10);bind(o);vines.append(o)
    for center,z0,z1,radius,turns in [(0,.87,1.64,.24,1.6),(-.13,.15,.90,.10,1.5),(.21,.15,.90,.10,1.5)]:
        for phase in [0,math.pi]:
            points=[]
            for i in range(90):
                t=i/89;phi=t*math.tau*turns+phase;p=Vector((center+radius*math.cos(phi),-radius*math.sin(phi),z0+(z1-z0)*t));co,no,_,_=nearest(p);points.append(co+no*.012)
            o=tube('Kudzu Body Vine',points,[.012]*len(points),material('Vine'),rings=140,sides=10);bind(o);vines.append(o)
    join('Kudzu Bound Vines',vines)
    leaves=[]
    for i,(px,py,size,angle) in enumerate([(282,650,.19,2.8),(349,721,.23,3.0),(461,684,.23,3.35),(423,780,.18,2.7),(231,768,.17,3.6),(318,861,.23,3.1),(444,876,.17,3.4),(338,990,.19,3.1),(178,953,.20,2.9),(564,944,.22,3.4)]):
        p=k.point(px,py,-.5);co,no,_,_=nearest(p);anchor=co+no*.018;o=small_leaf('Kudzu Body Leaf '+str(i),anchor,size,angle);bind(o,co);leaves.append(o)
    join('Kudzu Bound Leaves',leaves)
