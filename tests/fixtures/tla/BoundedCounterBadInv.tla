---- MODULE BoundedCounterBadInv ----
EXTENDS Integers

CONSTANT MaxValue

(* --algorithm BoundedCounterBadInv
variables counter = 0;
begin
  Increment:
    while counter < MaxValue do
      counter := counter + 1;
    end while;
end algorithm; *)

\* Inv is too weak to be inductive: it admits counter = MaxValue (so the
\* algorithm reaches it), but says counter \in 0..(MaxValue-1). The Init
\* obligation will pass (the initial state has counter = 0), but the
\* Consec obligation will fail when counter = MaxValue-1 increments to
\* MaxValue, which is outside Inv.
Inv == /\ counter \in 0..(MaxValue-1)
       /\ pc \in {"Increment", "Done"}

Property == counter <= MaxValue

====
