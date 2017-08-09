[**Table of Contents**](index.md)

# Git Info

## Getting Started
* [Git Basics](https://git-scm.com/book/en/v2/Getting-Started-Git-Basics)
* [Git Book](https://git-scm.com/book/en/v2)
* [Git Bootcamp and Cheat Sheet](https://docs.python.org/devguide/gitbootcamp.html)

### General Information
* Snapshots, not Differences

* Nearly every operation is local

* Integrity - SHA-1 Hash (40 Characters)

* 3 States that files can reside in:
    * Committed - Safely stored in the local database
    * Modified - Changed, not commited
    * Staged - Marked to go into the next commit

* fetch imports commits from a remote repo into your local repo.
* Commits are stored as remote branches instead of normal local branches.
* pull = fetch + merge
* git pull --rebase  origin   ← Same as git pull but instead of git merge, git rebase
* git pull --rebase  origin  == fetch + rebase
* Pull Request is a mechanism for a developer to notify team members that they have completed a feature.

## Useful git Commands

|Git task|	Notes|	Git commands|
|--------|-------|--------------|
| config | List the current config file |  git config --list |
| | Configure the author name and email address to be used with your commits. Note that Git strips some characters (for example trailing periods) from user.name.| git config --global user.name "Sam Smith"|
| | |git config --global user.email sam@example.com|
| | |git config --global http.proxy http://my-proxy.com |
| | | git config --global https.proxy https://my-proxy.com |
| | Alias for pull to do a fetch + rebase (no merge) | pull.rebase=true |
|Create a new local repository| | git init|
| Check out a repository | Create a working copy of a local repository:	| git clone /path/to/repository |
| | For a remote server, use:	| git clone username@host:/path/to/repository|
| Add files |  Add one or more files to staging (index):|git add filename |
| | Track new files |git add * |
| |  | git add *.c |
| | | git add file.c |
| Commit | Commit changes to head (but not yet to the remote repository):	| git commit -m "Commit message"|
| | Commit any files you've added with git add, and also commit any files you've changed since then:	| git commit -a |
| | Commit and signoff, opens editor to add comments | git commit -s |
| | Commit without running precommit tests | git commit -n |
| | To modify the comment of your last commit, before a push | git commit —amend |
| Squash commits | Squash all commits into one before a push | git log --oneline |
| | Interactively | git rebase -i (commit hash) |
| | Squash all commits | git rebase - root -i |
| Push | Send changes to the master branch of your remote repository:	| git push origin master|
| Status |	List the files you've changed and those you still need to add or commit:	|git status|
| | Short status | git status -s |
| diff | What changes were made | git diff  file.c |
| | git diff  --staged |
| rm | Remove a file | git rm file.c |
| mv | rename a file | git mv file1.c  file2.c |
|Connect to a remote repository| If you haven't connected your local repository to a remote server, add the server to be able to push to it:|git remote add origin <server>|
| Log | List all the commits to this repo | git log |
| | List one line logs | git log --oneline |
| | List the files that were changed in each commit | git log --stat |
| | | git log —names-only |
| | |git —name-status |
| | List changeset from 2 commits ago | git log  -p  -2 |
| | Format the logs | git log  --pretty=format:"%h  %s"  --graph | 
| | List commits since 2 weeks ago | git log  --since=2.weeks|
| | List all currently configured remote repositories:|	git remote -v|
|Branches| Create a new branch and switch to it:	| git checkout -b <branchname>|
| | Switch from one branch to another:	|git checkout <branchname>|
| | List all the branches in your repo, and also tell you what branch you're currently in:	|git branch --all |
| | Delete the feature branch:	|git branch -d <branchname> |
| | Push the branch to your remote repository, so others can use it:	| git push origin <branchname> |
| | Push all branches to your remote repository:	| git push --all origin |
| | Delete a branch on your remote repository: | git push origin :<branchname> |
| Update from the remote repository | Fetch and merge changes on the remote server to your working directory:	| git pull |
| |To merge a different branch into your active branch:	| git merge <branchname> | 
| | View all the merge conflicts: | git diff |
| | View the conflicts against the base file: | git diff --base <filename> | 
| | Preview changes, before merging: | git diff <sourcebranch> <targetbranch> |
| | After you have manually resolved any conflicts, you mark the changed file:	| git add <filename> |
| Tags | You can use tagging to mark a significant changeset, such as a release:	|  git tag 1.0.0 <commitID> |
| | List all tags | git tag |
| | CommitId is the leading characters of the changeset ID, up to 10, but must be unique. Get the ID using:	| git log |
| | Push all tags to remote repository:	|  git push --tags origin |
| | Checkout version v1.2.1 with tag: v1.2.1 |git checkout v1.2.1 |
| show | List info | git show |
| | | git show —pretty=(short-medium-full-fuller-raw) |
| Undo local changes |  If you mess up, you can replace the changes in your working tree with the last content in head: Changes already added to the index, as well as new files, will be kept. |  git checkout -- <filename> |
| | Instead, to drop all your local changes and commits, fetch the latest history from the server and point your local master branch at it, do this:	| git fetch origin |
| | | git reset --hard origin/master |
| To sync with the origin | List the current origin | git remote -v |
| fetch and rebase (Instead of fetch and merge) | | git pull  --rebase |
| Search |  Search the working directory for foo():	| git grep "foo()" |
| Help | |git help  <verb> |
| | | git help config| 
| stash | Switch branches without doing a commit | git stash |
| | List the stashes | git stash list |
| | Switch branch and do other work | git checkout branch-2 |
| | After the commit and push, return to branch-1 | git checkout branch-1 |
| | Apply the stash to be right back before the interruption | git stash apply | 
| | Can also pop the stash stack | git stash pop |
| | Unapply a stash | git stash show -p stash@{0} |
| | | git apply -R |
| | Create a branch from a stash | git stash branch testchanges |
| | 
| | | |