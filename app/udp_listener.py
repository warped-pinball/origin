import asyncio
import json
import logging
from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models, schemas
from datetime import datetime

logger = logging.getLogger(__name__)


class UDPListener:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.transport = None

    class Protocol(asyncio.DatagramProtocol):
        def __init__(self):
            super().__init__()

        def connection_made(self, transport):
            self.transport = transport
            logger.info("UDP Listener started")

        def datagram_received(self, data, addr):
            message = data.decode()
            logger.debug(f"Received UDP message from {addr}: {message}")
            try:
                data_json = json.loads(message)
                # Process the message in a separate task to avoid blocking the loop
                # In a real app, might want to use a queue
                asyncio.create_task(self.process_message(data_json, addr))
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {addr}: {message}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")

        async def process_message(self, data: dict, addr):
            # Create a new database session for this operation
            db = SessionLocal()
            try:
                # Basic validation using Pydantic
                # Assuming the payload matches GameStateCreate schema roughly
                # But we need to handle logic: find active game for machine, or create one

                machine_id = data.get("machine_id")
                if not machine_id:
                    logger.warning(f"No machine_id in message from {addr}")
                    return

                # Update machine last_seen
                machine = (
                    db.query(models.Machine)
                    .filter(models.Machine.id == machine_id)
                    .first()
                )
                if not machine:
                    # Auto-create machine if it doesn't exist? Or just log error?
                    # For now, let's auto-create for smoother dev experience
                    machine = models.Machine(
                        id=machine_id, name=f"Machine {machine_id}", ip_address=addr[0]
                    )
                    db.add(machine)
                    db.commit()
                    db.refresh(machine)
                else:
                    machine.last_seen = datetime.now()
                    machine.ip_address = addr[0]
                    db.commit()

                # Find active game
                game = (
                    db.query(models.Game)
                    .filter(
                        models.Game.machine_id == machine_id,
                        models.Game.is_active == True,
                    )
                    .first()
                )

                # If no active game, create one?
                # Or should there be a specific "start game" message?
                # For simplicity, if we receive state and no active game exists, create one.
                if not game:
                    game = models.Game(machine_id=machine_id)
                    db.add(game)
                    db.commit()
                    db.refresh(game)

                # Record game state
                game_state = models.GameState(
                    game_id=game.id,
                    seconds_elapsed=data.get("seconds_elapsed", 0),
                    ball=data.get("ball", 1),
                    player_up=data.get("player_up", 1),
                    scores=data.get("scores", []),
                )
                db.add(game_state)
                db.commit()

                logger.info(f"Processed state for Machine {machine_id}, Game {game.id}")

            except Exception as e:
                logger.error(f"Error in process_message: {e}")
            finally:
                db.close()

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, protocol = await loop.create_datagram_endpoint(
            lambda: self.Protocol(), local_addr=(self.host, self.port)
        )
        logger.info(f"UDP Listener bound to {self.host}:{self.port}")

    def stop(self):
        if self.transport:
            self.transport.close()
