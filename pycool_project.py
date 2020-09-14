# -*- coding: utf-8 -*-
"""PyCool_Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nF_wSMkTHHEiIOoPZDPlOj2davG2ISQt
"""


from __future__ import print_function, division

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import time
import os
import copy
from torch.utils.data import Dataset, DataLoader

import matplotlib.pyplot as plt

from sklearn.metrics import confusion_matrix
import itertools
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
import random

import plotly.graph_objects as go

plt.ion()   # interactive mode

class TrainModel():
  def __init__(self, dataset_dir, batch_size, img_size, channels):
    self.dataset_dir = dataset_dir
    self.batch_size = batch_size

    self.img_size = img_size
    self.channels = channels

  def compute_mean_and_std(self, mean, std):
    if mean == None:
      data_transforms_wo_normalization = {
      'train': transforms.Compose([
          transforms.RandomResizedCrop(self.img_size),
          transforms.RandomHorizontalFlip(),
          transforms.ToTensor(),
        ])
      }

      print("Computing Mean and STD")
      train_dataset = datasets.ImageFolder(os.path.join(self.dataset_dir, 'train'),
                                                data_transforms_wo_normalization['train'])

      train_dataloader = DataLoader(train_dataset, batch_size=self.batch_size,
                                                  shuffle=True)

      train_dataloader = DataLoader(train_dataset, batch_size=len(train_dataset), shuffle=True)
      data = next(iter(train_dataloader))

      custom_mean = []
      custom_std = []

      
      for channels in range(self.channels):
        custom_mean.append(data[0][:, channels, :, :].mean())
        custom_std.append(data[0][:, channels, :, :].std())
        print("...", end='')

      self.mean = custom_mean
      self.std = custom_std
    else:
      self.mean = mean
      self.std = std

  def load_dataset(self, mean, std):
    self.compute_mean_and_std(mean, std)
    data_transforms_with_normalization = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(self.img_size),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std)
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(self.img_size),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std)
        ]),
    }

    train_dataset = datasets.ImageFolder(os.path.join(self.dataset_dir, 'train'),
                                            data_transforms_with_normalization['train'])

    train_dataloader = DataLoader(train_dataset, batch_size=self.batch_size,
                                                shuffle=True)

    val_dataset = datasets.ImageFolder(os.path.join(self.dataset_dir, 'val'),
                                              data_transforms_with_normalization['val'])

    val_dataloader = DataLoader(val_dataset, batch_size=self.batch_size,
                                                shuffle=True)
    
    dataloader = {'train': train_dataloader,
                'val': val_dataloader}

    dataset_sizes = {'train': len(train_dataset),
                  'val': len(val_dataset)}

    classnames = {'train': train_dataset.classes,
                'val': val_dataset.classes}

    dataset = {'train': train_dataset,
                  'val': val_dataset}

    predictions = {'train': None,
                   'val': None,
                   'test': None}

    self.dataloader = dataloader 
    self.dataset_sizes = dataset_sizes
    self.classnames = classnames
    self.dataset = dataset
    self.predictions = predictions

  def set_device(self, device):
    self.device =  device

  def set_seed(self, seed):
    """Set Seed"""

    random.seed(seed)
    np.random.seed(seed)

    torch.manual_seed(seed)
    if torch.cuda.is_available():
      torch.cuda.manual_seed(seed)
      torch.cuda.manual_seed_all(seed)

      torch.backends.cudnn.deterministic = True
      torch.backends.cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)

  def build_densenet_transfer_learning_model(self, model):
    self.model = model
    # model_ft = self.model
    num_ftrs = self.model.classifier.in_features
    self.model.classifier = nn.Linear(num_ftrs, len(self.classnames['train']))

    self.model = self.model.to(self.device)

    self.criterion = nn.CrossEntropyLoss()

    # Observe that all parameters are being optimized
    self.optimizer = optim.SGD(self.model.parameters(), lr=0.001, momentum=0.9)

    # Decay LR by a factor of 0.1 every 7 epochs
    self.scheduler = lr_scheduler.StepLR(self.optimizer, step_size=7, gamma=0.1)

  def train_model(self, num_epochs=25):
    since = time.time() # To measure time taken to build and train the model

    best_model_wts = copy.deepcopy(self.model.state_dict()) # Save weight of best model
    best_acc = 0.0 # Save best accuracy

    self.training_loss = []
    self.val_loss = []

    self.training_accuracy = []
    self.val_accuracy = []

    for epoch in range(num_epochs):
      print('Epoch {}/{}'.format(epoch, num_epochs - 1))
      print('-' * 10)

      # Each epoch has its training and validation
      for phase in ['train', 'val']:
        if phase == 'train':
          self.model.train()
        else:
          self.model.eval()

        running_loss = 0.0
        running_corrects = 0

        for inputs, labels in self.dataloader[phase]:
          inputs = inputs.to(self.device) # Move data to GPU if you are using GPU
          labels = labels.to(self.device) # Move data to GPU if you are using GPU

          self.optimizer.zero_grad() # Set gradients to zero so it does not accumulate

          with torch.set_grad_enabled(phase == 'train'): # Train in train phase
            outputs = self.model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = self.criterion(outputs, labels) # Compare ground truth with outputs

            # Backward propagation if in train mode
            if phase == 'train':
              loss.backward()
              self.optimizer.step()

          # Compute loss and accuracy
          running_loss += loss.item() * inputs.size(0)
          
          
          running_corrects += torch.sum(preds == labels.data)

        if phase =='train':
          self.scheduler.step()

        
        epoch_loss = running_loss / self.dataset_sizes[phase]
        epoch_acc = running_corrects.double() / self.dataset_sizes[phase]

        if phase == 'train':
          self.training_loss.append(epoch_loss)
          self.training_accuracy.append(epoch_acc)
        else:
          self.val_loss.append(epoch_loss)
          self.val_accuracy.append(epoch_acc)

        print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

        # deep copy the model
        if phase == 'val' and epoch_acc > best_acc:
          best_acc = epoch_acc
          best_model_wts = copy.deepcopy(self.model.state_dict())

      print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    self.model.load_state_dict(best_model_wts) # Load the best model weights

  def plot_loss_graph(self):
    fig = plt.figure()
    plt.plot(self.training_loss, color='blue')
    plt.plot(self.val_loss, color='red')
    plt.legend(['Train Loss', 'Val Loss'], loc='upper right')
    plt.xlabel('Number of epoch completed')
    plt.ylabel('Loss')

  def plot_accuracy_graph(self):
    fig = plt.figure()
    plt.plot(self.training_accuracy, color='blue')
    plt.plot(self.val_accuracy, color='red')
    plt.legend(['Train Accuracy', 'Val Accuracy'], loc='upper left')
    plt.xlabel('Number of epoch completed')
    plt.ylabel('Accuracy')

  @torch.no_grad() # this functions execution omits gradient tracking.
  def test_model(self):
    self.model.eval()

    for inputs, labels in self.dataloader['val']:
      inputs = inputs.to(self.device) # Move data to GPU if you are using GPU
      labels = labels.to(self.device) # Move data to GPU if you are using GPU

      self.optimizer.zero_grad() # Set gradients to zero so it does not accumulate

      with torch.set_grad_enabled(False): # Train in train phase
        outputs = self.model(inputs)
        _, preds = torch.max(outputs, 1)

  @torch.no_grad() # this functions execution omits gradient tracking.
  def get_preds(self, pred_type):
    pred_type_preds = torch.tensor([]).cuda()
    for batch in self.dataloader[pred_type]:
        images, labels = batch
        images, labels = images.cuda(), labels.cuda() 

        preds = self.model(images)
        preds = preds.cuda()
        pred_type_preds = torch.cat(
            (pred_type_preds, preds)
            ,dim=0
        )
        
    self.predictions[pred_type] = pred_type_preds.max(1)[1].tolist()
    self.cmt = torch.zeros(len(self.classnames['train']),len(self.classnames['train']), dtype=torch.int64)
    for i in range(len(self.predictions[pred_type])):
      tl = self.dataset[pred_type].targets[i]
      pl = self.predictions[pred_type][i]

      self.cmt[tl, pl] = self.cmt[tl, pl] + 1

    self.compute_accuracy_precision_recall()
    plt.figure(figsize=(5,5))
    self.plot_confusion_matrix(self.cmt, self.classnames[pred_type])

  def plot_confusion_matrix(self, cm, classes, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt), horizontalalignment="center", color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

  def compute_accuracy_precision_recall(self):
    tp = [0] * self.cmt.shape[1]
    fp = [0] * self.cmt.shape[1]
    fn = [0] * self.cmt.shape[1]
    total_per_class = [0] * self.cmt.shape[1]

    for row in range(self.cmt.shape[1]):
      total_per_class[row] = self.cmt[row].sum()

      for column in range(self.cmt.shape[1]):
        
        # Compute True Positive For Each Class
        if row == column:
          tp[row] += self.cmt[row][column]

        # Compute False Positive and False Negative
        else:
          fp[column] += self.cmt[row][column]
          fn[row] += self.cmt[row][column]

    tp = tp[0:len(self.classnames['val'])]
    fp = fp[0:len(self.classnames['val'])]
    fn = fn[0:len(self.classnames['val'])]
    total_per_class = total_per_class[0:len(self.classnames['val'])]
    # Precision
    self.precision = np.array(tp) / (np.array(fp) + np.array(tp))
    self.plot_table(self.precision)

    # Recall
    self.recall = np.array(tp) / (np.array(fn) + np.array(tp))
    self.plot_table(self.recall)

    # Accuracy
    self.accuracy = np.round(np.array(tp).sum() / np.array(total_per_class).sum(), 3)

  def plot_table(self, res):
    row_headers = self.classnames['val']
    

    needed_result = res[0:len(self.classnames['val'])]
    header = list(row_headers)
    header.append('Average')
    result = list(needed_result)
    result.append(np.average(needed_result))

    values = [header, np.round(result, 3)]

    fig = go.Figure(data=[go.Table(
      columnorder = [1,2],
      columnwidth = [5,5],
      header = dict(
        values = [['<b>Class Names</b>'], ['<b>Values</b>']],
        line_color='darkslategray',
        fill_color='royalblue',
        align=['left','center'],
        font=dict(color='white', size=12),
        height=40
      ),
      cells=dict(
        values=values,
        line_color='darkslategray',
        fill=dict(color=['paleturquoise', 'white']),
        align=['left', 'center'],
        font_size=12,
        height=30)
        )
    ])
    fig.update_layout(width=500, height=500)
    fig.show()