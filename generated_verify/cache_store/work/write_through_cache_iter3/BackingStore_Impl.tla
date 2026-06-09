---- MODULE BackingStore_Impl ----
EXTENDS Integers, TLC

CONSTANTS Keys, Vals, Missing

Domain == Vals \cup {Missing}

(* --algorithm BackingStore
variables
  store = [k \in Keys |-> Missing];

begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          store[k] := v;
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "edde184a" /\ chksum(tla) = "a9173f8e")
VARIABLE store

vars == << store >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> Missing]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  store' = [store EXCEPT ![k] = v]
        \/ /\ TRUE
           /\ store' = store

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv == store \in [Keys -> Domain]

Property == store \in [Keys -> Domain]
====
