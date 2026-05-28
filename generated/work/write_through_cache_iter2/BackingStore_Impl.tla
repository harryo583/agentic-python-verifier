---- MODULE BackingStore_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Keys, Vals

Zero == CHOOSE v \in Vals : \A w \in Vals : v <= w

(* --algorithm BackingStore
variables
  storePresent = [k \in Keys |-> FALSE],
  storeVal = [k \in Keys |-> Zero];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          storePresent[k] := TRUE ||
          storeVal[k] := v;
        end with;
      or
        with k \in Keys do
          skip;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "27586ac5" /\ chksum(tla) = "25c883ae")
VARIABLES storePresent, storeVal

vars == << storePresent, storeVal >>

Init == (* Global variables *)
        /\ storePresent = [k \in Keys |-> FALSE]
        /\ storeVal = [k \in Keys |-> Zero]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  /\ storePresent' = [storePresent EXCEPT ![k] = TRUE]
                  /\ storeVal' = [storeVal EXCEPT ![k] = v]
        \/ /\ \E k \in Keys:
                TRUE
           /\ UNCHANGED <<storePresent, storeVal>>

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

InvImpl ==
  /\ storePresent \in [Keys -> BOOLEAN]
  /\ storeVal \in [Keys -> Vals]

PropertyImpl == InvImpl
====
