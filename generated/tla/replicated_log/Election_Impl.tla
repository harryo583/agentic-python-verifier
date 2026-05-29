---- MODULE Election_Impl ----
EXTENDS Naturals, FiniteSets

CONSTANTS Nodes, MaxTerm

Roles == {"leader", "follower"}

(* --algorithm Election
variables
  role = [n \in Nodes |-> "follower"],
  term = [n \in Nodes |-> 0];
begin
  ELoop:
    while TRUE do
      either
        with n \in Nodes do
          await \A m \in Nodes : role[m] = "follower";
          role := [role EXCEPT ![n] = "leader"];
        end with;
      or
        with n \in Nodes do
          await role[n] = "leader";
          role := [role EXCEPT ![n] = "follower"];
        end with;
      or
        with n \in Nodes do
          await term[n] < MaxTerm;
          term := [m \in Nodes |-> term[n] + 1];
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "1686af37" /\ chksum(tla) = "7497fac3")
VARIABLES role, term

vars == << role, term >>

Init == (* Global variables *)
        /\ role = [n \in Nodes |-> "follower"]
        /\ term = [n \in Nodes |-> 0]

Next == \/ /\ \E n \in Nodes:
                /\ \A m \in Nodes : role[m] = "follower"
                /\ role' = [role EXCEPT ![n] = "leader"]
           /\ term' = term
        \/ /\ \E n \in Nodes:
                /\ role[n] = "leader"
                /\ role' = [role EXCEPT ![n] = "follower"]
           /\ term' = term
        \/ /\ \E n \in Nodes:
                /\ term[n] < MaxTerm
                /\ term' = [m \in Nodes |-> term[n] + 1]
           /\ role' = role

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Leaders == { n \in Nodes : role[n] = "leader" }

TypeOK ==
  /\ role \in [Nodes -> Roles]
  /\ term \in [Nodes -> 0..MaxTerm]

Inv == TypeOK /\ Cardinality(Leaders) <= 1
Property == Cardinality(Leaders) <= 1
====
