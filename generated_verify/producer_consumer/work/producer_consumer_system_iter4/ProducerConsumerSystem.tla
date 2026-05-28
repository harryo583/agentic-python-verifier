---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxVal, MaxItem

VARIABLES buffer, generated, nextItem, received, sum, pcQ, pcP, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, pc <- pcQ, Capacity <- Capacity, MaxVal <- MaxVal
P == INSTANCE Producer_Impl WITH generated <- generated, nextItem <- nextItem, pc <- pcP, MaxItem <- MaxItem
C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, pc <- pcC, MaxVal <- MaxVal, MaxLen <- MaxItem

vars == <<buffer, generated, nextItem, received, sum, pcQ, pcP, pcC>>

Init == Q!Init /\ P!Init /\ C!Init
Next == (Q!Next /\ UNCHANGED <<generated, nextItem, received, sum, pcP, pcC>>)
     \/ (P!Next /\ UNCHANGED <<buffer, received, sum, pcQ, pcC>>)
     \/ (C!Next /\ UNCHANGED <<buffer, generated, nextItem, pcQ, pcP>>)

Spec == Init /\ [][Next]_vars

SumOf(s) == LET F[i \in 0..Len(s)] == IF i = 0 THEN 0 ELSE F[i-1] + s[i] IN F[Len(s)]

IsPrefix(a, b) == Len(a) <= Len(b) /\ \A i \in 1..Len(a): a[i] = b[i]

BSeq(S, n) == UNION { [(1..k) -> S] : k \in 0..n }

Inv == /\ buffer \in BSeq(1..MaxVal, Capacity)
       /\ generated \in BSeq(1..MaxItem, MaxItem)
       /\ received \in BSeq(1..MaxVal, MaxItem)
       /\ nextItem \in 1..(MaxItem+1)
       /\ sum \in 0..(MaxItem * MaxVal)
       /\ pcQ \in {"Loop", "Done"}
       /\ pcP \in {"Loop", "Done"}
       /\ pcC \in {"Loop", "Done"}
       /\ Len(generated) = nextItem - 1
       /\ IsPrefix(received, generated)
       /\ received \o buffer = generated
       /\ sum = SumOf(received)

Property == /\ Len(buffer) \in 0..Capacity
            /\ IsPrefix(received, generated)
            /\ nextItem <= MaxItem + 1

====
