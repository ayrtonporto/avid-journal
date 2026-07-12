import Papers.TinyEvensPaperIntegrationTestOpencode.Paper

theorem thm_four_evens (a b c d : Nat) (ha : def_even a) (hb : def_even b) (hc : def_even c) (hd : def_even d) :
    def_even (a + b + c + d) := by
  have hab : def_even (a + b) := lem_even_sum ha hb
  have hcd : def_even (c + d) := lem_even_sum hc hd
  have hsum : def_even ((a + b) + (c + d)) := lem_even_sum hab hcd
  simpa [add_assoc] using hsum