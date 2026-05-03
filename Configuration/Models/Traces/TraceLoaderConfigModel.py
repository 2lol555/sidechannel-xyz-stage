from dataclasses import dataclass

@dataclass
class TraceLoaderConfigModel:
    target_path: str
    data_path: str = ''
