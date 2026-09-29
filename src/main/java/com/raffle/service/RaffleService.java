package com.raffle.service;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class RaffleService {

    public List<String> drawWinners(List<String> participants, int numberOfWinners) {
        if (participants == null || participants.isEmpty()) {
            throw new IllegalArgumentException("Debe haber al menos un participante");
        }
        if (numberOfWinners <= 0) {
            throw new IllegalArgumentException("El numero de ganadores debe ser mayor a 0");
        }
        if (numberOfWinners > participants.size()) {
            throw new IllegalArgumentException(
                "No se pueden sortear " + numberOfWinners +
                " ganadores con solo " + participants.size() + " participantes"
            );
        }

        List<String> shuffled = new ArrayList<>(participants);
        Collections.shuffle(shuffled);
        return shuffled.subList(0, numberOfWinners);
    }
}
