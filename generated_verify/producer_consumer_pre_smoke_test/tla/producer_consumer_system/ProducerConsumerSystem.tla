---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxItem, MaxLen

VARIABLES buffer, generated, next_item, received, sum, pcQ, pcP, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, Capacity <- Capacity, MaxLen <- MaxLen, pc <- pcQ
P == INSTANCE Producer_Impl WITH generated <- generated, next_item <- next_item, MaxItem <- MaxItem, MaxLen <- MaxLen, pc <- pcP
C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, MaxLen <- MaxLen, pc <- pcC

allVars == << buffer, generated, next_item, received, sum, pcQ, pcP, pcC >>

Init ==
  /\ Q!Init
  /\ P!Init
  /\ C!Init

Next ==
  \/ (Q!Next /\ UNCHANGED << generated, next_item, received, sum, pcP, pcC >>)
  \/ (P!Next /\ UNCHANGED << buffer, received, sum, pcQ, pcC >>)
  \/ (C!Next /\ UNCHANGED << buffer, generated, next_item, pcQ, pcP >>)

Spec == Init /\ [][Next]_allVars

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

IsPrefix(a, b) ==
  /\ Len(a) <= Len(b)
  /\ \A i \in 1..Len(a) : a[i] = b[i]

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

Inv ==
  /\ Q!Inv
  /\ P!Inv
  /\ C!Inv
  /\ buffer \in BSeq(1..10)
  /\ generated \in BSeq(1..MaxItem)
  /\ received \in BSeq(1..MaxItem)
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ next_item \in 1..(MaxItem+1)

Property ==
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ next_item <= MaxItem + 1

====
