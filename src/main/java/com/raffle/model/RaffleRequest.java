package com.raffle.model;

import java.util.List;

public record RaffleRequest(
    List<String> participants,
    int numberOfWinners
) {}
