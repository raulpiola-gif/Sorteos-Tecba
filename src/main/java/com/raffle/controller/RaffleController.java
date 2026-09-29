package com.raffle.controller;

import com.raffle.model.RaffleRequest;
import com.raffle.model.RaffleResponse;
import com.raffle.service.RaffleService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
public class RaffleController {

    private final RaffleService raffleService;

    public RaffleController(RaffleService raffleService) {
        this.raffleService = raffleService;
    }

    @PostMapping("/raffle")
    public ResponseEntity<?> raffle(@RequestBody RaffleRequest request) {
        try {
            List<String> winners = raffleService.drawWinners(
                request.participants(),
                request.numberOfWinners()
            );
            return ResponseEntity.ok(new RaffleResponse(winners));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }
}
