[**Table of Contents**](index.md)

## Sync with the github origin
Prior to pushing the code change it may be necessary to synchronize your cloned repo with the master repo that may have changed while you were working.

To synchronize your cloned master with the origin master and to rebase your changed on top of the changes of everyone else, do the following:

|Git task|Git command|
|--------|--------------|
|  List the Current origin  |  git remote -v |
|  Switch to the master branch |git checkout master |
| Fetch and Rebase | git pull  --rebase |
| Switch back to your branch |  git checkout my-fix |
| Put your changes on top of everyone elses | git rebase master |

## Push to github
* git push origin my-fix

## Create a Pull Request
* In a Browser, go to the correct repo: 
    * Frontend: [https://github.com/intel-hpdd/GUI](https://github.com/intel-hpdd/GUI)
    * Backend: [https://github.com/intel-hpdd/intel-manager-for-lustre](https://github.com/intel-hpdd/intel-manager-for-lustre)

* Click on the **Branches** tab.
* Find the branch named **my-fix**
* On the right hand side, click the button for **New pull request**

* Fill out a comment with the description of the change
* Choose Reviewers, Labels, Assignees, etc.
* Click **Create pull request**

## Copy the URL and request a code review
* Either assign reviewers directly in the pull request (**PR**), or, add a comment to request a code review in the PR.

### If the code review is approved by at least two developers, the gatekeeper will merge the pull request onto the master branch

### If comments are left in the PR page, then the developer is responsible for addressing each comment.
* If code changes are required, edit the code, save and commit as described above.
* Test any code changes.
* Rebase the branch onto the master as necessary.
* Re-push any changes to the same branch that was initially pushed.
```
git push origin my-fix
```