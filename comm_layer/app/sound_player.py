"""
Sound player for the Communication Layer.

Provides local audio playback using OS media player commands
for order completion and error alerts.
"""

import asyncio
import subprocess
from typing import Any, Dict, Optional
from pathlib import Path

from .core.transport import Transport, TransportConfig, TransportType, TransportError
from .core.logger import get_logger

logger = get_logger(__name__)

class SoundPlayer(Transport):
    """
    Local OS transport for sound playback.
    
    Handles audio file playback using OS media player commands
    for system notifications and alerts.
    """
    
    def __init__(self, config: TransportConfig):
        """
        Initialize sound player.
        
        Args:
            config: Transport configuration
        """
        super().__init__(config)
        self.logger = get_logger(f"{__name__}.{config.name}")
        
        # Extract configuration
        self.player_command = config.config.get('player_command', 'mpv')
        self.audio_files = config.config.get('audio_files', {})
        
        # Process management
        self.current_process = None
    
    async def initialize(self) -> None:
        """
        Initialize sound player.
        
        Validates audio files and player command availability.
        """
        try:
            self.logger.info("Initializing sound player")
            
            # Validate player command
            await self._validate_player_command()
            
            # Validate audio files
            await self._validate_audio_files()
            
            self.logger.info("Sound player initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sound player: {e}")
            raise TransportError(f"Sound player initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """
        Shutdown sound player.
        
        Stops any currently playing audio and cleanup resources.
        """
        try:
            self.logger.info("Shutting down sound player")
            
            if self.current_process:
                await self._stop_current_audio()
            
            self.logger.info("Sound player shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during sound player shutdown: {e}")
    
    async def is_healthy(self) -> bool:
        """
        Check if sound player is healthy.
        
        Returns:
            True if player command is available and audio files exist
        """
        try:
            # Check if player command is available
            result = await asyncio.create_subprocess_exec(
                self.player_command, "--version",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await result.wait()
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def play_sound(self, sound_type: str) -> None:
        """
        Play a sound by type.
        
        Args:
            sound_type: Type of sound to play (e.g., 'order_complete', 'error_alert')
            
        Raises:
            TransportError: If sound playback fails
        """
        try:
            if sound_type not in self.audio_files:
                raise TransportError(f"Unknown sound type: {sound_type}")
            
            audio_file = self.audio_files[sound_type]
            self.logger.info(f"Playing sound: {sound_type} ({audio_file})")
            
            await self._play_audio_file(audio_file)
            
        except Exception as e:
            self.logger.error(f"Failed to play sound {sound_type}: {e}")
            raise TransportError(f"Sound playback failed: {e}")
    
    async def play_order_complete(self) -> None:
        """
        Play order completion sound.
        
        Raises:
            TransportError: If sound playback fails
        """
        await self.play_sound('order_complete')
    
    async def play_error_alert(self) -> None:
        """
        Play error alert sound.
        
        Raises:
            TransportError: If sound playback fails
        """
        await self.play_sound('error_alert')
    
    async def play_custom_sound(self, audio_file: str) -> None:
        """
        Play a custom audio file.
        
        Args:
            audio_file: Path to the audio file to play
            
        Raises:
            TransportError: If sound playback fails
        """
        try:
            self.logger.info(f"Playing custom sound: {audio_file}")
            
            await self._play_audio_file(audio_file)
            
        except Exception as e:
            self.logger.error(f"Failed to play custom sound {audio_file}: {e}")
            raise TransportError(f"Custom sound playback failed: {e}")
    
    async def _validate_player_command(self) -> None:
        """Validate that the player command is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                self.player_command, "--version",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await result.wait()
            
            if result.returncode != 0:
                raise TransportError(f"Player command not available: {self.player_command}")
                
        except FileNotFoundError:
            raise TransportError(f"Player command not found: {self.player_command}")
    
    async def _validate_audio_files(self) -> None:
        """Validate that configured audio files exist."""
        for sound_type, audio_file in self.audio_files.items():
            if not Path(audio_file).exists():
                self.logger.warning(f"Audio file not found: {audio_file} for {sound_type}")
    
    async def _play_audio_file(self, audio_file: str) -> None:
        """
        Play an audio file using the configured player command.
        
        Args:
            audio_file: Path to the audio file to play
            
        Raises:
            TransportError: If playback fails
        """
        try:
            # Stop any currently playing audio
            if self.current_process:
                await self._stop_current_audio()
            
            # Start new audio playback
            self.current_process = await asyncio.create_subprocess_exec(
                self.player_command, audio_file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for playback to complete (non-blocking)
            asyncio.create_task(self._wait_for_playback_completion())
            
        except Exception as e:
            raise TransportError(f"Audio playback failed: {e}")
    
    async def _stop_current_audio(self) -> None:
        """Stop currently playing audio."""
        if self.current_process:
            try:
                self.current_process.terminate()
                await asyncio.wait_for(self.current_process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.current_process.kill()
                await self.current_process.wait()
            finally:
                self.current_process = None
    
    async def _wait_for_playback_completion(self) -> None:
        """Wait for current audio playback to complete."""
        if self.current_process:
            try:
                await self.current_process.wait()
                self.logger.info("Audio playback completed")
            except Exception as e:
                self.logger.error(f"Audio playback error: {e}")
            finally:
                self.current_process = None

# Register with transport factory
TransportFactory.register(TransportType.LOCAL_OS, SoundPlayer) 