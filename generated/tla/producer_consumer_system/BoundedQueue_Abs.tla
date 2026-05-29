---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity

VARIABLES queue

vars == << queue >>

BoundedSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Init == queue = << >>

Enqueue(v) ==
  /\ Len(queue) < Capacity
  /\ v \in 1..10
  /\ queue' = Append(queue, v)

Dequeue ==
  /\ Len(queue) > 0
  /\ queue' = Tail(queue)

Next == (\E v \in 1..10 : Enqueue(v)) \/ Dequeue

Spec == Init /\ [][Next]_vars

Inv ==
  /\ queue \in BoundedSeq(1..10, Capacity)

====
