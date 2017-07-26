[**Intel® Manager for Lustre\* Developer Resources Table of Contents**](README.md)

# Git Info

## Getting Started
* [Git Basics](https://git-scm.com/book/en/v2/Getting-Started-Git-Basics)
* [Git Book](https://git-scm.com/book/en/v2)


 ### Commit Changes
 ``` 
 Runs tests, lint and flow and then you can add comments 
 ```
* git commit -s 
```
    — OR -
 No tests, line and flow — you can add comments
 ```
* git commit -n
```
    — OR -
 Simple commit with message
```
  * git commit -m "This is my fix"


 ### To modify the comment of your last commit, before a push
 
  * git commit —amend
 
 ```
 To sync with the origin
 ```
 
 ```List the current origin```
  * git remote -v
  * git checkout master

``` fetch and rebase (Instead of fetch and merge)```
  * git pull  --rebase
  * git checkout my-new-branch

``` Put your changes on top of what everyone else has done```
  * git rebase master	
 
```Push the branch to the origin```

  * git push origin my-new-branch


## git Commands


### List Files inside each commit

* git log —names-only
* git —name-status

* git show
* git show —pretty=(short|medium|full|fuller|raw)


### CONFIG
* git config --list
* git config --global user.name "John Smith "
* git config --global user.email john.smith@abc123.com
* git config --global http.proxy http://my-proxy.com
* git config --global https.proxy https://my-proxy.com


### Help
* git help  <verb>
* git help config

### Init
* git init
 
### Add - Track new files
* git add *.c
* git add file.c

### Modify last commit before a push
* git commit  --amend

### List Tags
* git tag

### Checkout a previous revision from a tag
* git checkout v1.2.1
  * where, v1.2.1 is the tag name.

### Remote - What's the Parent Repo?
* git remote -v
 
### Status
* git status
* git status -s

### Log
* git log --stat
* git log  -p  -2
* git log  --pretty=format:"%h  %s"  --graph
* git log  --since=2.weeks

### Diff
* git diff  file.c
* git diff  --staged
 
* git rm file.c
* git mv file1.c  file2.c
 

### General Information
* Snapshots, not Differences

* Nearly every operation is local

* Integrity - SHA-1 Hash (40 Characters)

* 3 States that files can reside in:
    * Committed - Safely stored in the local database
    * Modified - Changed, not commited
    * Staged - Marked to go into the next commit


