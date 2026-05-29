---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxItem

VARIABLES buffer, pcQ,
          generated, nextItem, pcP,
          received, sum, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, pc <- pcQ
P == INSTANCE Producer_Impl WITH generated <- generated, nextItem <- nextItem, pc <- pcP
C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, pc <- pcC

qVars == << buffer, pcQ >>
pVars == << generated, nextItem, pcP >>
cVars == << received, sum, pcC >>
vars  == << buffer, pcQ, generated, nextItem, pcP, received, sum, pcC >>

Init == Q!Init /\ P!Init /\ C!Init

Next ==
  \/ (Q!Next /\ UNCHANGED pVars /\ UNCHANGED cVars)
  \/ (P!Next /\ UNCHANGED qVars /\ UNCHANGED cVars)
  \/ (C!Next /\ UNCHANGED qVars /\ UNCHANGED pVars)

Spec == Init /\ [][Next]_vars

RECURSIVE SumSeq(_)
SumSeq(s) == IF s = << >> THEN 0 ELSE Head(s) + SumSeq(Tail(s))

IsPrefix(a, b) ==
  /\ Len(a) <= Len(b)
  /\ \A i \in 1..Len(a) : a[i] = b[i]

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Inv ==
  /\ buffer \in BoundedSeq(1..MaxItem, Capacity)
  /\ pcQ \in {"Loop", "Finish", "Done"}
  /\ generated \in BoundedSeq(1..MaxItem, MaxItem)
  /\ nextItem \in 1..(MaxItem+1)
  /\ pcP \in {"ProduceLoop", "Finish", "Done"}
  /\ received \in BoundedSeq(1..MaxItem, MaxItem)
  /\ sum \in 0..(MaxItem*MaxItem)
  /\ pcC \in {"ConsumeLoop", "Finish", "Done"}
  /\ Len(generated) = nextItem - 1
  /\ \A i \in 1..Len(generated) : generated[i] = i
  /\ \A i \in 1..Len(received)  : received[i]  = i
  /\ sum = SumSeq(received)
  /\ IsPrefix(received, generated)
  /\ Len(received) + Len(buffer) <= Len(generated)
  /\ \A i \in 1..Len(buffer) : buffer[i] = Len(received) + i

Property ==
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ nextItem <= MaxItem + 1

====
