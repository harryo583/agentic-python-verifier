---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences

CONSTANT Capacity

VARIABLE queue

vars == << queue >>

BoundedSeqs == UNION { [1..n -> 1..10] : n \in 0..Capacity }

Init == queue = << >>

Enqueue(v) == /\ Len(queue) < Capacity
              /\ v \in 1..10
              /\ queue' = Append(queue, v)

Dequeue == /\ Len(queue) > 0
           /\ queue' = Tail(queue)

Next == (\E v \in 1..10 : Enqueue(v)) \/ Dequeue

Spec == Init /\ [][Next]_vars

Inv == queue \in BoundedSeqs

Property == Len(queue) \in 0..Capacity
====
