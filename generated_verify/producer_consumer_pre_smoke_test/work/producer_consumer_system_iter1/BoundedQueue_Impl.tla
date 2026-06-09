---- MODULE BoundedQueue_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxLen

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

(* --algorithm BoundedQueue
variables buffer = << >>;
begin
  Loop:
    while TRUE do
      either
        with v \in 1..10 do
          await Len(buffer) < Capacity;
          buffer := Append(buffer, v);
        end with;
      or
        await Len(buffer) > 0;
        buffer := Tail(buffer);
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "b634b9e7" /\ chksum(tla) = "46c311ec")
VARIABLE buffer

vars == << buffer >>

Init == (* Global variables *)
        /\ buffer = << >>

Next == \/ /\ \E v \in 1..10:
                /\ Len(buffer) < Capacity
                /\ buffer' = Append(buffer, v)
        \/ /\ Len(buffer) > 0
           /\ buffer' = Tail(buffer)

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv ==
  /\ buffer \in BSeq(1..10)
  /\ Len(buffer) \in 0..Capacity
  /\ pc \in {"Loop", "Done"}

Property == Len(buffer) \in 0..Capacity

====
