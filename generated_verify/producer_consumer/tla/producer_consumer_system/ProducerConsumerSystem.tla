---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxItem, MaxLen

VARIABLES buffer, generated, nextItem, received, runningSum,
          pcQ, pcP, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, pc <- pcQ
P == INSTANCE Producer_Impl     WITH generated <- generated, nextItem <- nextItem, pc <- pcP
C == INSTANCE Consumer_Impl     WITH received <- received, runningSum <- runningSum, pc <- pcC

vars == << buffer, generated, nextItem, received, runningSum, pcQ, pcP, pcC >>

Init == Q!Init /\ P!Init /\ C!Init
Next == (Q!Next /\ UNCHANGED << generated, nextItem, received, runningSum, pcP, pcC >>)
     \/ (P!Next /\ UNCHANGED << buffer, received, runningSum, pcQ, pcC >>)
     \/ (C!Next /\ UNCHANGED << buffer, generated, nextItem, pcP, pcQ >>)

Spec == Init /\ [][Next]_vars

IsPrefix(s, t) == Len(s) <= Len(t) /\ (\A i \in 1..Len(s) : s[i] = t[i])

Inv == /\ Q!Inv
       /\ P!Inv
       /\ C!Inv
       /\ Len(buffer) \in 0..Capacity
       /\ IsPrefix(received, generated)
       /\ nextItem \in 1..(MaxItem+1)

Property == /\ Len(buffer) \in 0..Capacity
            /\ IsPrefix(received, generated)
            /\ nextItem <= MaxItem + 1
====
