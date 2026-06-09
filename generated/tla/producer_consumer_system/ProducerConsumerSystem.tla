---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

VARIABLES buffer, pcQ,
          generated, nextItem, pcP,
          received, sum, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, pc <- pcQ, Capacity <- 3
P == INSTANCE Producer_Impl     WITH generated <- generated, nextItem <- nextItem, pc <- pcP, MaxItem <- 3
C == INSTANCE Consumer_Impl     WITH received <- received, sum <- sum, pc <- pcC, MaxLen <- 3

vars == << buffer, pcQ, generated, nextItem, pcP, received, sum, pcC >>

Init == Q!Init /\ P!Init /\ C!Init
Next == (Q!Next /\ UNCHANGED << generated, nextItem, pcP, received, sum, pcC >>)
        \/ (P!Next /\ UNCHANGED << buffer, pcQ, received, sum, pcC >>)
        \/ (C!Next /\ UNCHANGED << buffer, pcQ, generated, nextItem, pcP >>)

Spec == Init /\ [][Next]_vars

IsPrefix(s, t) == Len(s) <= Len(t) /\ (\A i \in 1..Len(s) : s[i] = t[i])

Inv == /\ Q!Inv
       /\ P!Inv
       /\ C!Inv
       /\ Len(buffer) \in 0..3
       /\ IsPrefix(received, generated)
       /\ nextItem \in 1..4

Property == /\ Len(buffer) \in 0..3
            /\ IsPrefix(received, generated)
            /\ nextItem <= 4

====