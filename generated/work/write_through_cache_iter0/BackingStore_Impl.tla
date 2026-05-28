---- MODULE BackingStore_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Keys, Vals, Missing

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
        with k \in Keys do
          skip;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "2afd85ae" /\ chksum(tla) = "a20385ad")
VARIABLE store

vars == << store >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> Missing]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  store' = [store EXCEPT ![k] = v]
        \/ /\ \E k \in Keys:
                TRUE
           /\ store' = store

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

InvImpl ==
  /\ DOMAIN store = Keys
  /\ \A k \in Keys : store[k] \in (Vals \cup {Missing})

PropertyImpl == InvImpl
====
