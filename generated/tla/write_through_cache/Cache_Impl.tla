---- MODULE Cache_Impl ----
EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS Keys, Values, Missing

(* --algorithm Cache
variables cache = [k \in Keys |-> Missing];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Values do
          cache := [cache EXCEPT ![k] = v];
        end with;
      or
        with k \in Keys do
          cache := [cache EXCEPT ![k] = Missing];
        end with;
      or
        skip;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "ce1ed5e7" /\ chksum(tla) = "b185d8bc")
VARIABLES cache, pc

vars == << cache, pc >>

Init == (* Global variables *)
        /\ cache = [k \in Keys |-> Missing]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E k \in Keys:
                   \E v \in Values:
                     cache' = [cache EXCEPT ![k] = v]
           \/ /\ \E k \in Keys:
                   cache' = [cache EXCEPT ![k] = Missing]
           \/ /\ TRUE
              /\ cache' = cache
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ cache' = cache

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ cache \in [Keys -> Values \cup {Missing}]
  /\ pc \in {"Loop", "Finish", "Done"}

Property == cache \in [Keys -> Values \cup {Missing}]

====
