"""Local mesh constraints for offline corrective sculpting, never live physics."""
import numpy as np


def relax_surface(points,rest,edges,movable,triangles=None,stretch=1.8,iterations=240):
    points=points.copy();mass=movable.astype(float)
    edges=edges[np.any(movable[edges],axis=1)];a,b=edges.T
    lengths=np.maximum(.002,np.linalg.norm(rest[b]-rest[a],axis=1))
    if triangles is not None:
        triangles=triangles[np.any(movable[triangles],axis=1)]
        n=np.cross(rest[triangles[:,1]]-rest[triangles[:,0]],rest[triangles[:,2]]-rest[triangles[:,0]])
        area=np.linalg.norm(n,axis=1);keep=area>1e-9
        triangles=triangles[keep];area=area[keep];normals=n[keep]/area[:,None]
    for _ in range(iterations):
        total=np.zeros_like(points);counts=np.zeros(len(points))
        vector=points[b]-points[a];distance=np.linalg.norm(vector,axis=1)
        error=distance-np.clip(distance,lengths*.45,lengths*stretch)
        active=np.abs(error)>1e-7
        correction=vector*(error/np.maximum(distance,1e-10)/np.maximum(mass[a]+mass[b],1))[:,None]
        np.add.at(total,a,correction*mass[a,None]);np.add.at(total,b,-correction*mass[b,None])
        np.add.at(counts,a,active);np.add.at(counts,b,active)
        if triangles is not None:
            i,j,k=triangles.T;u=points[j]-points[i];v=points[k]-points[i]
            signed=np.einsum('ij,ij->i',np.cross(u,v),normals)
            error=np.maximum(0,area*.12-signed)
            g1=np.cross(v,normals);g2=np.cross(normals,u);g0=-g1-g2
            denom=sum(mass[idx]*np.einsum('ij,ij->i',g,g) for idx,g in [(i,g0),(j,g1),(k,g2)])
            factor=error/np.maximum(denom,1e-14)
            for idx,g in [(i,g0),(j,g1),(k,g2)]:
                np.add.at(total,idx,g*(factor*mass[idx])[:,None]);np.add.at(counts,idx,error>1e-10)
        if not np.any(counts):break
        delta=total/np.maximum(1,counts[:,None])*.65
        points+=delta
    return points


def defects(points,rest,edges,triangles):
    n=np.cross(rest[triangles[:,1]]-rest[triangles[:,0]],rest[triangles[:,2]]-rest[triangles[:,0]])
    moved=np.cross(points[triangles[:,1]]-points[triangles[:,0]],points[triangles[:,2]]-points[triangles[:,0]])
    flipped=int(np.count_nonzero(np.einsum('ij,ij->i',n,moved)<-1e-16))
    length=np.maximum(.002,np.linalg.norm(rest[edges[:,1]]-rest[edges[:,0]],axis=1))
    strained=int(np.count_nonzero(np.linalg.norm(points[edges[:,1]]-points[edges[:,0]],axis=1)>2*length))
    return {'flipped':flipped,'stretched':strained}
