---- MODULE bounded_counter ----
EXTENDS Integers, TLC

CONSTANTS MaxValue

(* --algorithm BoundedCounter
variables counter = 0;
begin
  Loop:
    while TRUE do
      Increment:
        if counter < MaxValue then
          counter := counter + 1;
        else
          counter := counter;
        end if;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "bfe0c965" /\ chksum(tla) = "f643842f")
VARIABLES counter, pc

vars == << counter, pc >>

Init == (* Global variables *)
        /\ counter = 0
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ pc' = "Increment"
        /\ UNCHANGED counter

Increment == /\ pc = "Increment"
             /\ IF counter < MaxValue
                   THEN /\ counter' = counter + 1
                   ELSE /\ counter' = counter
             /\ pc' = "Loop"

Next == Loop \/ Increment

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv ==
  /\ counter \in 0..MaxValue
  /\ pc \in {"Loop", "Increment"}

Property == counter <= MaxValue
====
