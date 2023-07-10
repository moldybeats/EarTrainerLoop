from datetime import time
import pydub
import simpleaudio
import time
import toml
import random


DEBUG = False


class Sound:
    def __init__(self, filenames, sequential=False):
        if isinstance(filenames, str):
            self.filenames = [self.cleaned_filename(filenames)]
        else:
            self.filenames = [self.cleaned_filename(filename) for filename in filenames]
        self.sequential = sequential

    def play(self):
        if len(self.filenames) == 1:
            wav_obj = simpleaudio.WaveObject.from_wave_file(self.filenames[0])
        else:
            audio_segments = []
            for filename in self.filenames:
                audio_segment = pydub.AudioSegment.from_wav(filename)
                audio_segments.append(audio_segment)

            combined_audio = None

            for audio_segment in audio_segments:
                if combined_audio is None:
                    combined_audio = audio_segment
                else:
                    if self.sequential:
                        combined_audio = combined_audio + audio_segment
                    else:
                        # When combining, lower the volume of each audio segment
                        # to avoid clipping
                        combined_audio = combined_audio.overlay(audio_segment - 6)

            wav_obj = simpleaudio.WaveObject(
                combined_audio.raw_data,
                combined_audio.channels,
                combined_audio.sample_width,
                combined_audio.frame_rate,
            )

        wav_obj.play()

    def cleaned_filename(self, filename):
        return filename.replace('#', 'sh').replace('b', 'flat')


class ProgramStep:
    def __init__(self, duration):
        self.is_running = False
        self.start_time = None
        self.duration = duration

    def start(self):
        if DEBUG:
            print(f'{self}::start')
        self.is_running = True
        self.start_time = time.time()

    @property
    def elapsed_ms(self):
        if not self.start_time:
            return None

        return int((time.time() - self.start_time) * 1000)

    def stop(self):
        if DEBUG:
            print(f'{self}::stop [{self.elapsed_ms} ms]')
        self.is_running = False
        self.start_time = None

    @property
    def is_complete(self):
        return not self.is_running

    def step(self):
        if self.elapsed_ms > self.duration:
            self.stop()


class ProgramStep_PlayNote(ProgramStep):
    def __init__(self, note, duration):
        super().__init__(duration)
        self.note = note

    def start(self):
        super().start()
        self.note.sound.play()

    def __repr__(self):
        return f'ProgramStep_PlayNote: {self.note.name} ({self.duration} ms)'


class ProgramStep_PlayChord(ProgramStep):
    def __init__(self, chord, duration):
        super().__init__(duration)
        self.chord = chord

    def start(self):
        super().start()
        self.chord.sound.play()

    def __repr__(self):
        return f'ProgramStep_PlayChord: {self.chord.name} ({self.duration} ms)'


class ProgramStep_PlayIdentity(ProgramStep):
    def __init__(self, identity, duration):
        super().__init__(duration)
        self.identity = identity

    def start(self):
        super().start()
        self.identity.sound.play()

    def __repr__(self):
        return f'ProgramStep_PlayIdentity: {self.identity.name} ({self.duration} ms)'


class Program:
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps
        self.is_running = False
        self.current_step_idx = -1
        self.current_step = None

    def start(self):
        if DEBUG:
            print(f'{self.name}::start')

        self.current_step_idx = 0
        self.current_step = self.steps[0]
        self.current_step.start()
        self.is_running = True

    def stop(self):
        if DEBUG:
            print(f'{self.name}::stop')

        self.is_running = False
        self.current_step_idx = 0
        self.current_step = None

    @property
    def is_complete(self):
        return not self.is_running

    def step(self):
        self.current_step.step()

        if self.current_step.is_complete:
            self.current_step_idx += 1
            if self.current_step_idx >= len(self.steps):
                self.stop()
            else:
                self.current_step = self.steps[self.current_step_idx]
                self.current_step.start()

    def __repr__(self):
        return f'Program: {self.name}'


class Note:
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self, note_name, octave):
        self.note_name = note_name
        self.octave = octave
        self.identity = Identity(note_name)
        self.sound = Sound(f'./samples/note/{self.name}.wav')

    @property
    def name(self):
        return f'{self.note_name}{self.octave}'

    def add_semitones(self, semitones):
        idx = self.NOTES.index(self.note_name)

        new_note_idx = idx + semitones
        new_note_octave = self.octave
        if new_note_idx >= len(self.NOTES):
            new_note_idx -= len(self.NOTES)
            new_note_octave += 1

        new_note_name = self.NOTES[new_note_idx]

        return Note(new_note_name, new_note_octave)

    def add_interval(self, interval):
        return self.add_semitones(interval.semitones)

    def __repr__(self):
        return f'Note: {self.name}'


class Interval:
    SEMITONE_MAP = {
        'unison':  0,
        'min 2nd': 1,
        'maj 2nd': 2,
        'min 3rd': 3,
        'maj 3rd': 4,
        '4th':     5,
        'dim 5th': 6,
        '5th':     7,
        'min 6th': 8,
        'maj 6th': 9,
        'min 7th': 10,
        'maj 7th': 11,
        'octave':  12,
    }

    def __init__(self, interval, root_note):
        self.name = interval
        self.first_note = root_note
        self.second_note = root_note.add_interval(self)
        self.identity = Identity(interval)

    @property
    def semitones(self):
        return self.SEMITONE_MAP[self.name]

    def __repr__(slef):
        return f'Interval: {self.name} ({self.first_name.name}/{self.second_note.name})'


class Chord:
    INTERVAL_MAP = {
        'maj': ['maj 3rd', '5th'],
        'min': ['min 3rd', '5th'],
        'dim': ['min 3rd', 'dim 5th'],
    }

    def __init__(self, chord_name, octave):
        self.chord_name = chord_name
        self.octave = octave

        root_note_name, chord_type = chord_name.split(' ')
        root_note = Note(root_note_name, octave)

        intervals = self.INTERVAL_MAP[chord_type]
        self.notes = [root_note]
        for interval_name in intervals:
            interval = Interval(interval_name, root_note)
            self.notes.append(root_note.add_interval(interval))

        filenames = []
        for note in self.notes:
            filenames.append(f'./samples/note/{note.name}.wav')
        self.sound = Sound(filenames, sequential=False)

        self.identity = Identity(chord_name)

    @property
    def name(self):
        return f'{self.chord_name}{self.octave}'

    def __repr__(self):
        return f'Chord: {self.name}'


class Identity:
    def __init__(self, identity):
        self.name = identity

        identity_parts = identity.split(' ')
        filenames = []
        for part in identity_parts:
            filenames.append(f'./samples/identity/{part}.wav')
        self.sound = Sound(filenames, sequential=True)

    def __repr__(self):
        return f'Identity: {self.name}'


class ConfigFile:
    def __init__(self, filename):
        self.filename = filename
        self.config = toml.load(filename)

    def read_programs(self):
        return self.read_note_programs() + \
               self.read_interval_programs() + \
               self.read_chord_programs()

    @property
    def settings(self):
        return self.config['settings']

    @property
    def octave_range(self):
        start = self.settings['octave_range'][0]
        end = self.settings['octave_range'][1]
        return range(start, end + 1)

    def read_note_programs(self):
        note_programs = self.config['programs']['notes'] or []
        note_duration = self.settings['note_duration']
        identity_duration = self.settings['identity_duration']

        programs = []

        for note_name in note_programs:
            for octave in self.octave_range:
                note = Note(note_name, octave)
                program = Program(f'Note - {note.name}', [
                    ProgramStep_PlayNote(note, note_duration),
                    ProgramStep_PlayIdentity(note.identity, identity_duration),
                ])
                programs.append(program)

        return programs

    def read_interval_programs(self):
        interval_programs = self.config['programs']['intervals'] or []
        note_duration = self.settings['note_duration']
        identity_duration = self.settings['identity_duration']

        programs = []

        for interval_name in interval_programs:
            for note_name in Note.NOTES:
                for octave in self.octave_range:
                    root_note = Note(note_name, octave)
                    interval = Interval(interval_name, root_note)
                    program = Program(f'Interval - {interval.name} ({root_note.name})', [
                        ProgramStep_PlayNote(interval.first_note, note_duration),
                        ProgramStep_PlayNote(interval.second_note, note_duration),
                        ProgramStep_PlayIdentity(interval.identity, identity_duration),
                    ])
                    programs.append(program)

        return programs

    def read_chord_programs(self):
        chord_programs = self.config['programs']['chords'] or []
        note_duration = self.settings['note_duration']
        identity_duration = self.settings['identity_duration']

        programs = []

        for chord_type in chord_programs:
            for note_name in Note.NOTES:
                chord_name = f'{note_name} {chord_type}'
                for octave in self.octave_range:
                    chord = Chord(chord_name, octave)
                    program = Program(f'Chord - {chord.name}', [
                        ProgramStep_PlayChord(chord, note_duration),
                        ProgramStep_PlayIdentity(chord.identity, identity_duration),
                    ])
                    programs.append(program)

        return programs

    def __repr__(self):
        return f'ConfigFile: {self.filename}'


class ProgramRunner:
    def __init__(self):
        config_file = ConfigFile('./config.toml')
        self.programs = config_file.read_programs()
        self.current_program = None

    def get_random_program(self):
        idx = random.randint(0, len(self.programs)-1)
        return self.programs[idx]

    def run(self):
        while True:
            if not self.current_program:
                self.current_program = self.get_random_program()
                self.current_program.start()
                print(f'* {self.current_program.name}')

            self.current_program.step()

            if self.current_program.is_complete:
                self.current_program = None


if __name__ == '__main__':
    runner = ProgramRunner()

    for prog in runner.programs:
        steps = ', '.join([str(s) for s in prog.steps])
        print(f'{prog}: {steps}')
    print(f'{len(runner.programs)} programs')
    
    runner.run()
