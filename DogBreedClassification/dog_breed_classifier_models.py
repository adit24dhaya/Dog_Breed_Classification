# -*- coding: utf-8 -*-
"""Dog Breed Classifier Models.ipynb

Automatically generated by Colaboratory.

"""

import numpy as np
import pandas as pd
import os , cv2 , random , time , shutil , csv
import tensorflow as tf
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from tqdm import tqdm
import scipy
from tensorflow.compat.v1 import ConfigProto,GPUOptions

# Commented out IPython magic to ensure Python compatibility.
np.random.seed(42)
# %matplotlib inline
import json
import os
import cv2
import keras
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Model
from keras.layers import BatchNormalization, Dense, GlobalAveragePooling2D,Lambda,Dropout,InputLayer,Input
from keras.utils import to_categorical
from tensorflow.keras.preprocessing.image import load_img

# Data directories
train_path = 'C:/Users/User/Desktop/input/train/'
test_path = 'C:/Users/User/Desktop/input/test/'

labels_df = pd.read_csv('C:/Users/User/Desktop/input/labels.csv')

labels_df.head()

labels_df.shape

print(f"number of images in training set {len(os.listdir(train_path))}")
print(f"number of images in testing set {len(os.listdir(test_path))}")

dog_breeds = sorted(list(set(labels_df.breed)))
numClass = len(dog_breeds)
print(numClass)
print(dog_breeds[:10])

class_to_num = dict(zip(dog_breeds,range(numClass)))
class_to_num

(train_path+labels_df.id+'.jpg')[0]

cv2.imread((train_path+labels_df.id+'.jpg')[0]).shape

plt.imshow(cv2.imread((train_path+labels_df.id+'.jpg')[0]))

labels_df['file_name'] = labels_df['id'].apply(lambda x:train_path+f"{x}.jpg")

labels_df.head()

labels_df['breed'] = labels_df.breed.map(class_to_num)

labels_df.head()

y = to_categorical(labels_df.breed)

"""FEATURE EXTRACTION"""

from keras.applications.inception_resnet_v2 import InceptionResNetV2,preprocess_input as resnet_preprocess
from keras.applications.inception_v3 import InceptionV3,preprocess_input as inception_preprocess
from keras.applications.xception import Xception,preprocess_input as xception_preprocess
#from keras.applications.nasnet import NASNetLarge, preprocess_input as nasnet_preprocess
from keras.layers import concatenate

input_shape = (331,331,3)
input_layer = Input(shape= input_shape)

#inception Resnet
preprocessor_resnet = Lambda(resnet_preprocess)(input_layer)
inception_resnet = InceptionResNetV2(weights = 'imagenet',include_top = False,input_shape = input_shape,pooling = 'avg')(preprocessor_resnet)


#Inception V3
preprocessor_inception = Lambda(inception_preprocess)(input_layer)
inception_v3 = InceptionV3(weights = 'imagenet',include_top = False,input_shape = input_shape,pooling = 'avg')(preprocessor_inception)

preprocessor_xception = Lambda(xception_preprocess)(input_layer)
xception =Xception(weights = 'imagenet',include_top = False,input_shape = input_shape,pooling = 'avg')(preprocessor_xception)

merge = concatenate([inception_v3,inception_resnet,xception])
model = Model(inputs = input_layer,outputs = merge)

model.summary()

model.save('feature_extractor.h5')

from keras.utils import plot_model
plot_model(model,show_shapes = True)

model.output.shape

len(model.trainable_weights)

def feature_extractor(df):
    img_size = (331,331,3)
    data_size = len(df)
    batch_size = 10
    X = np.zeros([data_size,5632],dtype=np.uint8)
    # y = np.zeros([data_size,120],dtype = np.uint8)
    datagen = ImageDataGenerator()
    generator = datagen.flow_from_dataframe(df,
                                           x_col='file_name',class_mode=None,
                                           batch_size=10, shuffle=False,target_size=(img_size[:2]),color_mode='rgb')
    i=0
    for input_batch in tqdm(generator):
        input_batch=model.predict(input_batch)
        X[i*batch_size:(i+1)*batch_size]=input_batch
        i+=1
        if i*batch_size >= data_size:
            break;
    return X

X=feature_extractor(labels_df)

X.shape

from keras.callbacks import EarlyStopping,ModelCheckpoint,ReduceLROnPlateau
EarlyStop_Callback = keras.callbacks.EarlyStopping(monitor = 'val_loss',patience = 20,restore_best_weights = True)
checkpoint = ModelCheckpoint('C:/Users/Adi/Desktop/input/working/checkpoint',monitor = 'val_loss',mode= 'min',save_best_only = True)
lr = ReduceLROnPlateau(monitor = 'val_loss',factor = 0.5,patience = 3,min_lr = 0.00001)
my_callback = [EarlyStop_Callback,checkpoint]

"""## Model Creation"""

dnn = keras.models.Sequential([
    InputLayer(X.shape[1:]),
    Dropout(0.7),
    Dense(numClass,activation = 'softmax')
])
dnn.compile(optimizer = 'adam',
            loss = 'categorical_crossentropy',
            metrics = ['accuracy'])

h = dnn.fit(X,y,
           batch_size = 128,
           epochs = 60,
           validation_split = 0.1,
           callbacks = my_callback)

fig , (ax1,ax2) = plt.subplots(2,1,figsize = (12,12))
ax1.plot(h.history['loss'],color = 'b',label = "loss")
ax1.plot(h.history['val_loss'],color = 'r',label = 'val_loss')
ax1.set_xticks(np.arange(1,60,1))
ax1.set_yticks(np.arange(0,1,0.1))
ax1.legend(['loss','val_loss'],shadow = True)

ax2.plot(h.history['accuracy'],color = 'green',label = 'accuracy')
ax2.plot(h.history['val_accuracy'],color = 'red',label = 'val_accuracy')
ax2.legend(['accuracy','val_accuracy'],shadow = True)
plt.show()

"""## Prediction"""

test_data = []
ids = []
for pic in os.listdir(test_path):
    ids.append(pic.split('.')[0])
    test_data.append(test_path+pic)

test_dataframe = pd.DataFrame({'file_name':test_data})

test_features = feature_extractor(test_dataframe)

y_pred = dnn.predict(test_features)

def get_key(val):
    for key,value in class_to_num.items():
        if val == value:
            return key

pred_codes = np.argmax(y_pred,axis = 1)
predictions = []
for i in pred_codes:
    predictions.append(get_key(i))

test_dataframe['breed'] = predictions

np.set_printoptions(suppress = True)

pd.set_option('display.float_format',lambda x: '%.10f' % x)

"""## For submissions in Kaggle (Optional)"""

submission = pd.DataFrame(y_pred,columns = dog_breeds)
submission['id'] = ids

submission.set_index('id')

submission.to_csv('submission.csv',index = False)

"""## Plotting some Results"""

plt.figure(figsize = (6,6))

for index,data in test_dataframe[:20].iterrows():
    img = data['file_name']
    label = data['breed']
    img = cv2.imread(img)
    plt.imshow(img)
    plt.xlabel(label,fontsize = (15))
    plt.tight_layout()
    plt.show()
