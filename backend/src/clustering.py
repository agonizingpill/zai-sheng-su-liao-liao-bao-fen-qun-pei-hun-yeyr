from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np

def cluster(bales):
    if len(bales)<6:raise ValueError('至少6个检验完整料包才能分3群')
    X=np.array([[float(b.melt_index),float(b.moisture),float(b.pvc_ppm)]for b in bales])
    scaler=StandardScaler();z=scaler.fit_transform(X)
    if len(np.unique(z,axis=0))<3:raise ValueError('有效特征不足3种，不能稳定分群')
    km=KMeans(n_clusters=3,n_init=10,random_state=42);labels=km.fit_predict(z)
    score=float(silhouette_score(z,labels))
    centers=scaler.inverse_transform(km.cluster_centers_)
    # Sort labels by melt index so group labels keep a useful, deterministic domain order.
    order=np.argsort(centers[:,0]);mapping={int(old):int(new) for new,old in enumerate(order)}
    return [mapping[int(x)] for x in labels],{'rows':len(bales),'features':['melt_index','moisture','pvc_ppm'],'silhouette':round(score,4),'inertia':round(float(km.inertia_),4),'centers':[[round(float(x),3) for x in centers[i]]for i in order],'seed':42,'n_init':10,'algorithm':'StandardScaler + KMeans(k=3)','evaluation':'无监督轮廓系数用于描述当前分群，不是留出集预测准确率'}
