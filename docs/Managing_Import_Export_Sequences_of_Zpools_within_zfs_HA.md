### background

IML manages zfs device access by handling zpool imports and exports with exclusive locks.
Care is taken to only ever import a zpool Read-Write on a single host at a time.
Zpools maybe imported as read-only on one host whilst imported read/write on another for a short period during a device scan.
Software locks are used to protect from races during import-export sequences occurring on different threads and processes running on the same host.

### import-export sequences

When IML processes a zpool to either scan datasets to detect existing file systems or to create or remove filesystem information, the relevant zpool has to be imported and then exported on the relevant host.
This usually consists of listing the zpools currently imported, and if the desired zpool is not within the list, attempting to import the zpool. Once imported the relevant operation can be completed and depending on the operation the zpool is then exported (after a device scan or stopping a target) or remains imported (after starting a target).

### locking

Race conditions can exist during a import-export sequence due to the multithreaded/multiprocessor nature of IML. 

Given the situation where tA is attempting to mount a lustre target on pA on hA and at the same time a device scan is performed on a separate thread on the same host, two example scenarios of race conditions are listed below:

abbreviations: t=thread, p=pool, h=host

#### scenario 1:
1. tA lists imported zpools on hA, not finding pA
2. tB lists imported zpools on hA , not finding pA
3. tB imports pA on hA
4. tA attempts to import pA on hA but fails as its already imported

#### scenario 2:
1. tB lists imported zpools on hA , not finding pA
2. tB imports pA on hA
3. tA lists imported zpools on hA and finds pA already imported
4. tB finishes device scan operation on pA and exports pA from hA
5. tA attempts to create dataset on pA which it assumes is already imported on hA, operation fails because pool is not imported on hA 
 
Thread lock objects have been used to try to prevent these races from occurring, using the premise that when performing an import export transition, the zpool in question will not be imported and exported by another thread during the period of the transition.

The failure due to the race condition in scenario 2 is averted using locking. tB takes a lock on pA before step #2, therefore before #3, when tA attempts to lock on pA, it has to wait until tB releases the lock (which happens after step #4). The new order of events in scenario 2 when locks are utilised becomes 1, 2, 4, 3, 5 and the failure is averted.

###  inter-process locking

Another consideration is what happens when multiple processes are active which run IML code and perform independent import-export sequences on zpools.

This can occur when the IML daemon is operational at the same time as the pacemaker application triggers an event in a resource agent (IML RA is named 'Target') calling the chroma-agent cli using the system shell directly (for example 'chroma-agent unmount_target --target <uuid>').

In this situation, both processes could be running import-export sequences on the same zpool both unaware of each other's thread specific locks. These locks exist in separate process memory spaces, solutions which allow process threads to be aware of locks in separate processes include inter-process communication, inter-process shared memory or global/file locks.

### global or file locks

File locks exist as unix files, therefore locks can be detected by any process with access to the local filesystem. This enable us to protect against interference between import-export zpool sequences occurring in different processes running IML code.

File locks are created on zpool during transitions in a specified directory and removed after desired sequence. Lock implementation is re-entrant, meaning a given thread can lock multiple times (nesting), and each time the reference count for that thread/lock object combination is incremented. Only when the top level lock call is unlocked and reference count becomes 0, is the lock released (removing the lock file and allowing other threads to acquire a lock on the zpool).

### lock implementation

Lock directory is cleared and re-created on zfs device_driver_initialization which occurs on agent startup.

