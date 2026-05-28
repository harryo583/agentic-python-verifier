---- MODULE BoundedQueue_Impl ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxVal

(* --algorithm BoundedQueue
variables buffer = <<>>;
begin
  Loop:
    while TRUE do
      either
        with v \in 1..MaxVal do
          if Len(buffer) < Capacity then
            buffer := Append(buffer, v);
          end if;
        end with;
      or
        if Len(buffer) > 0 then
          buffer := Tail(buffer);
        end if;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "c5b7be0c" /\ chksum(tla) = "c5521515")
VARIABLE buffer

vars == << buffer >>

Init == (* Global variables *)
        /\ buffer = <<>>

Next == \/ /\ \E v \in 1..MaxVal:
                IF Len(buffer) < Capacity
                   THEN /\ buffer' = Append(buffer, v)
                   ELSE /\ TRUE
                        /\ UNCHANGED buffer
        \/ /\ IF Len(buffer) > 0
                 THEN /\ buffer' = Tail(buffer)
                 ELSE /\ TRUE
                      /\ UNCHANGED buffer

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

BSeq(S, n) == UNION { [(1..k) -> S] : k \in 0..n }

Inv == /\ buffer \in BSeq(1..MaxVal, Capacity)
       /\ pc \in {"Loop", "Done"}

Property == Len(buffer) \in 0..Capacity
====
