[**Table of Contents**](index.md)

# Contributing to IML Quick Guide

## General 
* [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)

## Prerequisites
* Install the [VS Code IDE/Editor](https://code.visualstudio.com/?wt.mc_id=adw-brandcore-editor&gclid=EAIaIQobChMI1arV9dDF1QIVDmt-Ch1quQYGEAAYASAAEgJ-oPD_BwE) and install the following plugins:
    * ESLint
    * Prettier - ESLint
    * Flow Language Support
    * Jest
* Create a virtual Vagrant cluster described [here](https://github.com/intel-hpdd/Vagrantfiles/blob/master/README.md)
* For the desciption that follows, it will be assumed that the Vagrant file and virtual machine info resides in: **~/vagrant-projects/proj1** 

## Contributing to the IML Frontend
### Clone the GUI repo
```
cd ~/vagrant-projects/proj1
git clone git@github.com:intel-hpdd/GUI.git 
```
### Create a branch 
```
cd GUI
git checkout -b  proj1-fix
```
### Validate that the correct branch has been selected
```
git branch
```
### Work on the branch
```
Use VS Code and open ~/vagrant-projects/proj1/GUI
```
## Contributing to the IML Backend
