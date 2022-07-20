import numpy as np
from numpy.random import randn

from  tpsda.toroidal.psdamodel import ToroidalPSDA, train_ml, train_map, \
                               KappaPrior_KL, Scoring


import matplotlib.pyplot as plt
from  tpsda.subsphere.pca import Globe

from tpsda import one_hot

from pyllr.quick_eval import scoreslabels_2_eer_cllr_mincllr
from pyllr.plotting import DETPlot, tarnon_hist
from pyllr.utils import scoreslabels_2_tarnon
from pyllr.pav_rocch import ROCCH, PAV



def umodel( D, d, m, w=None, kappa=None):
    """
    Create a model with some given and some random parameters. The z and y
    priors are uniform.
    
    inputs:
        
        D: observation dimensionality

        d: (n,) hidden variable dimensionalities

        m: number of speaker variables: 0 <= m <= n
        
        w: (n,) positive hidden variable combination weights
                does not need to be length-normed, this will be done here
                if None, weights are made uniform
                
        kappa > 0: observation VMF noise concentration
                   if None, will be set to a somewhat concentrated value
    
    
    
    """
    n = len(d)
    assert d.sum() <= D
    assert 1 <= m <= n
    
    gamma = np.zeros(n)
    model =  ToroidalPSDA.random(D, d, m, w, kappa, gamma)
    return model

def sample_tr(model:ToroidalPSDA, ns=100, nr=10):
    """
    Sample labelled training data, with ns speakers and (exactly) nr 
    repetitions per speaker, so that the number of data points is ns*nr.
    
    Returns data, labels
    """
    print('sampling training data')
    labels = np.arange(ns).repeat(nr)
    X, Y, Z, Mu, labels = model.sample(labels)
    return X, labels

def sample_te(model:ToroidalPSDA, ns=100, ne=1, nt=10):
    """
    Sample labelled test data, with ns speakers and exactly ne enrollment data 
    points per speaker and exactly nt test data points per speaker.
    
    Returns:
        
        E: (ns*ne,D) enrollment data
        elabels: speaker labels for E
        
        T: (ns*nt,D) test data
        tlabels: speaker labels for T
        
        
        
    """
    print('sampling test data')
    elabels = np.arange(ns).repeat(ne)
    E, Y, Z, Mu, elabels = model.sample(elabels)
    tlabels = np.arange(ns).repeat(nt)
    t = len(tlabels)
    T = model.sample_data(Z,tlabels,model.sample_channels(t))
    return E, elabels, T, tlabels

def utrain(X,labels,d,m,niters=50,quiet=True):
    """
    Trains a model, with given d and m and uniform z and y priors on the given
    labelled data.
    
    
    
    """
    print('training model')
    model, obj = train_ml(d,m,niters,X,labels,uniformz=True,uniformy=True,
                          quiet=quiet)
    return model, obj


def marg_llh(model:ToroidalPSDA, X, labels):
    """
    marginal log-likelihood log P(X | labels, model)
    """
    return model.margloglh(X,labels=labels)


def pool(X,labels):
    """
    Pool (sum) data for each speaker. This should be used for multi-enroll
    trials.
    
    inputs:
        X: (t,D) t data points
        labels: speaker labels in the range 0 .. ns-1, with at least one
                data point for every speaker
                
    return:

        Xsum: (ns,D) summed data
        reduced labels: 0,1,...,ns-1             
    
    """
    L = one_hot.scipy_sparse_1hot_cols(labels)
    Xsum = L @ X
    ns = Xsum.shape[0]
    return Xsum, np.arange(ns)    
    


def test_scores(model:ToroidalPSDA, E, elabels, T, tlabels, multi_enroll=True):
    if multi_enroll:
        E, elabels = pool(E,elabels)
    sc = Scoring(model)
    left = sc.side(E)
    right = sc.side(T)
    scores = left.llrMatrix(right).ravel()
    labels = (elabels.reshape(-1,1) == tlabels).ravel().astype(int)
    return scores, labels




def test(model:ToroidalPSDA, E, elabels, T, tlabels, multi_enroll=True):
    scores, labels = test_scores(model, E, elabels, T, tlabels, multi_enroll)
    eer, cllr, mincllr = scoreslabels_2_eer_cllr_mincllr(scores,labels)
    return eer, cllr, mincllr
    

def train_test(m, d, Xtr, labels_tr, E, elabels, T, tlabels, multi_enroll=True):
    model, obj = utrain(Xtr,labels_tr,d,m)
    eer, cllr, mincllr = test(model, E, elabels, T, tlabels, multi_enroll)
    marg = marg_llh(model,T,tlabels)
    print(f"w={model.E.w}, kappa={model.kappa}")
    print('eer, Cllr, minCllr:',eer,cllr,mincllr)
    print('marg_llh:',marg)    
    
    
def shist(scores, labels, title=''):
    fig, ax = plt.subplots()
    tarnon_hist(*scoreslabels_2_tarnon(scores,labels), ax, title)
    plt.show()    
    
    
    
D = 128
m = 1
d = np.array([D//2,])
w = None
kappa = 100
model0 = umodel(D,d,m,w,kappa=kappa)  
ns, ne, nt = 500, 1, 10  
E, elabels, T, tlabels = sample_te(model0,ns,ne,nt)  
scores, labels = test_scores(model0, E, elabels, T, tlabels, False)  
eer, cllr, mincllr = scoreslabels_2_eer_cllr_mincllr(scores,labels)
marg = marg_llh(model0,T,tlabels)
print('oracle test:')
print('eer, Cllr, minCllr:',eer,cllr,mincllr)
print('marg_llh:',marg)    


model1 = umodel(D,d,m,w,kappa=kappa)  
scores, labels = test_scores(model1, E, elabels, T, tlabels, False)  
eer, cllr, mincllr = scoreslabels_2_eer_cllr_mincllr(scores,labels)
marg = marg_llh(model0,T,tlabels)
print('model1 test:')
print('eer, Cllr, minCllr:',eer,cllr,mincllr)
print('marg_llh:',marg)    


# print('\n')
# Xtr, labels_tr = sample_tr(model0,5000,10)    

# print(f'\ntraining with oracle structure (m={m})')
# train_test(m, d, Xtr, labels_tr, E, elabels, T, tlabels)

# m = 56
# dz = 1
# d = np.hstack([np.full(m,dz),[DY,]])

# print(f'\ntraining with m={m}')
# train_test(m, d, Xtr, labels_tr, E, elabels, T, tlabels)


