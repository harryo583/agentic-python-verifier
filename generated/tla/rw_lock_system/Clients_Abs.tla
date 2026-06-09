---- MODULE Clients_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Clients

VARIABLES client_state

vars == << client_state >>

Init == client_state = [c \in Clients |-> "idle"]

WritingSet == { c \in Clients : client_state[c] = "writing" }

StartRead(c) ==
  /\ client_state[c] = "idle"
  /\ client_state' = [client_state EXCEPT ![c] = "reading"]

FinishRead(c) ==
  /\ client_state[c] = "reading"
  /\ client_state' = [client_state EXCEPT ![c] = "idle"]

StartWrite(c) ==
  /\ client_state[c] = "idle"
  /\ WritingSet = {}
  /\ client_state' = [client_state EXCEPT ![c] = "writing"]

FinishWrite(c) ==
  /\ client_state[c] = "writing"
  /\ client_state' = [client_state EXCEPT ![c] = "idle"]

Next == \E c \in Clients :
  StartRead(c) \/ FinishRead(c) \/ StartWrite(c) \/ FinishWrite(c)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ client_state \in [Clients -> {"idle", "reading", "writing"}]
  /\ Cardinality(WritingSet) <= 1

Property == Inv
====
