from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np

FEATURES=['melt_index','moisture','pvc_ppm']

def cluster(bales):
    if len(bales)<6:raise ValueError('至少6个检验完整料包才能分3群')
    X=np.array([[float(b.melt_index),float(b.moisture),float(b.pvc_ppm)]for b in bales])
    scaler=StandardScaler();z=scaler.fit_transform(X)
    if len(np.unique(z,axis=0))<3:raise ValueError('有效特征不足3种，不能稳定分群')
    km=KMeans(n_clusters=3,n_init=10,random_state=42);labels=km.fit_predict(z)
    score=float(silhouette_score(z,labels))
    centers=scaler.inverse_transform(km.cluster_centers_)
    # Sort labels by melt index so group labels keep a useful, deterministic domain order.
    order=np.argsort(centers[:,0]);mapping={int(old):int(new)for new,old in enumerate(order)}
    labels=[mapping[int(x)]for x in labels]
    centers_z=km.cluster_centers_[order]
    thresholds=[max((float(np.linalg.norm(z[i]-centers_z[c]))for i,l in enumerate(labels)if l==c),default=0.0)for c in range(3)]
    result={'rows':len(bales),'features':FEATURES,'silhouette':round(score,4),'inertia':round(float(km.inertia_),4),'centers':[[round(float(x),3)for x in centers[i]]for i in order],'seed':42,'n_init':10,'algorithm':'StandardScaler + KMeans(k=3)','evaluation':'无监督轮廓系数用于描述当前分群，不是留出集预测准确率'}
    artifact={'features':FEATURES,'seed':42,'n_init':10,'scaler_mean':[float(x)for x in scaler.mean_],'scaler_scale':[float(x)for x in scaler.scale_],'centers_z':[[float(x)for x in row]for row in centers_z],'centers':result['centers'],'thresholds':thresholds}
    return labels,result,artifact

def assign_points(artifact,rows):
    mean=np.array(artifact['scaler_mean']);scale=np.array(artifact['scaler_scale'])
    centers_z=np.array(artifact['centers_z']);z=(np.array(rows,dtype=float)-mean)/scale
    out=[]
    for row in z:
        d=np.linalg.norm(centers_z-row,axis=1);c=int(np.argmin(d))
        out.append((c,float(d[c]),float(artifact['thresholds'][c])))
    return out
