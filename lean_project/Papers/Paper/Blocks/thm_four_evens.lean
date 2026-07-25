import Papers.Paper.Paper

theorem thm_four_evens (a b c d : Nat)
    (ha : def_even a) (hb : def_even b) (hc : def_even c) (hd : def_even d) :
    def_even (a + b + c + d) := by
  have hab : def_even (a + b) := lem_even_sum a b ha hb
  have hcd : def_even (c + d) := lem_even_sum c d hc hd
  obtain ⟨k1, hk1⟩ := hab
  obtain ⟨k2, hk2⟩ := hcd
  exact ⟨k1 + k2, by omega⟩
