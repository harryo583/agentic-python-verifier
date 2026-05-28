---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences

CONSTANT Capacity

VARIABLE queue

vars == << queue >>

Init == queue = << >>

Enqueue(v) ==
  /\ v \in 1..10
  /\ Len(queue) < Capacity
  /\ queue' = Append(queue, v)

Dequeue ==
  /\ Len(queue) > 0
  /\ queue' = Tail(queue)

Next == (\E v \in 1..10 : Enqueue(v)) \/ Dequeue

Spec == Init /\ [][Next]_vars

Inv ==
  /\ Len(queue) \in 0..Capacity
  /\ \A i \in 1..Len(queue) : queue[i] \in 1..10

====
