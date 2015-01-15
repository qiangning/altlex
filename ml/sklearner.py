import collections
import pickle

#import numpy

from sklearn.cross_validation import StratifiedKFold
from sklearn.externals import joblib

from chnlp.utils.utils import indexedSubset, balance

def load(filename):
    classifier = Sklearner()

    with open(filename + '.map', 'rb') as f:
        classifier.featureMap = pickle.load(f)
    classifier.model = joblib.load(filename)

    return classifier

class Sklearner:
    def __init__(self):
        self.featureMap = None
        self.reverseFeatureMap = None

    def _transform(self, features):
        if self.featureMap is None:
            self.featureMap = {}
            counter = 0
            for feature in features:
                for featureName in feature:
                    if featureName not in self.featureMap:
                        self.featureMap[featureName] = counter
                        counter += 1
        else:
            counter = len(self.featureMap)

        #change this to be a numpy array?
        X = []
        for feature in features:
            x = [0] * counter
            for featureName in feature:
                if featureName in self.featureMap:
                    x[self.featureMap[featureName]] = float(feature[featureName])
            X.append(x)
            
        return X

    def train(self, training, transform=True):
        X, Y = zip(*training)
        if transform:
            X = self._transform(X)
        self.model = self.classifier.fit(X, Y)
        return self.model

    def crossvalidate(self, training, n_folds=2):
        features, y = zip(*training)
        X = self._transform(features)
        skf = StratifiedKFold(y,
                              n_folds=n_folds,
                              random_state=1) #make sure we always use same data
    
        accuracy = []
        precisions = []
        recalls = []
        for train_index,test_index in skf:
            tri = set(train_index)
            X_train = indexedSubset(X, tri)
            y_train = indexedSubset(y, tri)

            #need to oversample here
            balancedData = balance(zip(X_train, y_train))

            clf = self.train(balancedData, False)
            
            tei = set(test_index)
            X_test = indexedSubset(X, tei)
            y_test = indexedSubset(y, tei)

            accuracy.append(self.accuracy(zip(X_test, y_test), False))
            precision,recall = self.metrics(zip(X_test, y_test), False)
            precisions.append(precision)
            recalls.append(recall)

        self.printResults(accuracy, precisions, recalls)
        
        #train the final classifier on all the data
        #need to oversample again
        return self.train(zip(X, y), False)

    def metrics(self, testing, transform=True):
        refsets = collections.defaultdict(set)
        testsets = collections.defaultdict(set)
        truepos = 0
        trueneg = 0
        falsepos = 0
        falseneg = 0

        labels = set()
        for i, (feats, label) in enumerate(testing):
            
            refsets[label].add(i)
            observed = self.classify(feats, transform)
            testsets[observed].add(i)
            labels.add(label)
            if observed == label:
                if label == True:
                    truepos += 1
                else:
                    trueneg += 1
            elif label == False:
                falsepos +=1
            else:
                falseneg += 1

        print(truepos, trueneg, falsepos, falseneg)

        try:
            precision = truepos/(truepos+falsepos)
        except ZeroDivisionError:
            precision = float('nan')

        try:
            recall = truepos/(truepos+falseneg)
        except ZeroDivisionError:
            recall = float('nan')

        return precision, recall

    def printResults(self, accuracy, precision, recall): #handle=sys.stdout
        if type(accuracy) == list:
            n_folds = len(accuracy)
            accuracy = sum(accuracy)
            precision = sum(precision)
            recall = sum(recall)
        else:
            n_folds = 1

        accuracy /= n_folds
        precision /= n_folds
        recall /= n_folds

        f_measure = 2 * precision * recall / (precision+recall)
        print('''
              Accuracy: {}
              True precision: {}
              True recall: {}
              True F-measure: {}
              '''.format(
                  accuracy,
                  precision,
                  recall,
                  f_measure
                  ))

        return f_measure
            
    def classify(self, features, transform=True):
        if transform:
            assert(type(features) == dict)
            X = self._transform([features])
        else:
            X = features
            
        result = self.model.predict(X)
        return result[0]

    def prob(self, features, transform=True):
        raise NotImplementedError
    
    def accuracy(self, testing, transform=True):
        X, Y = zip(*testing)
        if transform:
            X = self._transform(X)
        return self.model.score(X,Y)

    @property
    def numClasses(self):
        return self.model.classes_
    
    @property
    def _feature_importances(self):
        return self.model.feature_importances_

    def show_most_informative_features(self, n=50):
        if self.featureMap is None:
            return None
        if self.reverseFeatureMap is None:
            self.reverseFeatureMap = dict((v,k) for k,v in self.featureMap.items())
            self.featureImportances = []
            for i,f in enumerate(self._feature_importances):
                self.featureImportances.append((self.reverseFeatureMap[i], f))
            self.featureImportances = sorted(self.featureImportances,
                                             key=lambda x:x[1],
                                             reverse=True)
            
        for featureName,featureValue in self.featureImportances[:n]:
            print("{}\t{}".format(featureName, featureValue))
            
         #print(self.model.feature_importances_)

    def save(self, filename):
        joblib.dump(self.model, filename, compress=9)
        with open(filename + '.map', 'wb') as f:
            pickle.dump(self.featureMap, f)
