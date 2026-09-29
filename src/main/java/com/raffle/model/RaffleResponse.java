package com.raffle.model;

import java.util.List;

public record RaffleResponse(
    List<String> winners
) {}
