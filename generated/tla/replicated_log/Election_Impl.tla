---- MODULE Election_Impl ----
EXTENDS Naturals, FiniteSets

CONSTANTS Nodes, MaxTerm

(* --algorithm Election
variables
  role = [n \in Nodes |-> IF n = CHOOSE x \in Nodes : TRUE THEN "leader" ELSE "follower"];
  term = [n \in Nodes |-> 0];
begin
  Loop:
    while TRUE do
      with ldr \in Nodes do
        with maxT = CHOOSE m \in {term[n] : n \in Nodes} : \A n \in Nodes : term[n] <= m do
          await maxT < MaxTerm;
          role := [n \in Nodes |-> IF n = ldr THEN "leader" ELSE "follower"];
          term := [n \in Nodes |-> maxT + 1];
        end with;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "f05eace" /\ chksum(tla) = "e899beae")
VARIABLES role, term, pc

vars == << role, term, pc >>

Init == (* Global variables *)
        /\ role = [n \in Nodes |-> IF n = CHOOSE x \in Nodes : TRUE THEN "leader" ELSE "follower"]
        /\ term = [n \in Nodes |-> 0]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E ldr \in Nodes:
             LET maxT == CHOOSE m \in {term[n] : n \in Nodes} : \A n \in Nodes : term[n] <= m IN
               /\ maxT < MaxTerm
               /\ role' = [n \in Nodes |-> IF n = ldr THEN "leader" ELSE "follower"]
               /\ term' = [n \in Nodes |-> maxT + 1]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << role, term >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Leaders == { n \in Nodes : role[n] = "leader" }
AtMostOneLeader == Cardinality(Leaders) <= 1

TypeOK ==
  /\ role \in [Nodes -> {"leader", "follower"}]
  /\ term \in [Nodes -> 0..MaxTerm]
  /\ pc \in {"Loop", "Finish", "Done"}

Inv == TypeOK /\ AtMostOneLeader

Property == AtMostOneLeader
====
