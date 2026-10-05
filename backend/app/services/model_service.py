import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb

from app.schemas.prediction import ModelInfoResponse, PredictionResponse


class ModelService:
    """
    Singleton-style service that loads the XGBoost model and metadata once at startup,
    and handles inference and probability generation.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.model_path = Path(
            model_path or os.getenv("MODEL_PATH", base_dir / "models" / "merge_conflict_model.json")
        )
        self.metadata_path = Path(
            metadata_path or os.getenv("METADATA_PATH", base_dir / "models" / "model_metadata.json")
        )

        self.model: Optional[xgb.XGBClassifier] = None
        self.metadata: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self.load_error: Optional[str] = None

        # Default class mapping matching the LabelEncoder from training:
        # Index 0: combine_both, Index 1: keep_incoming, Index 2: keep_local
        self.classes: List[str] = ["combine_both", "keep_incoming", "keep_local"]
        self.class_mapping: Dict[int, str] = {
            0: "combine_both",
            1: "keep_incoming",
            2: "keep_local",
        }
        self.version: str = "v3"

    def load_model(self) -> bool:
        """
        Loads the native XGBoost model file and metadata JSON.
        Returns True if successful, False otherwise.
        """
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found at: {self.model_path}")

            # Initialize XGBClassifier and load serialized native model
            model = xgb.XGBClassifier()
            model.load_model(str(self.model_path))
            self.model = model

            # Load metadata if present
            if self.metadata_path.exists():
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

                self.version = self.metadata.get("version", "v3")
                loaded_classes = self.metadata.get("classes")
                if loaded_classes and isinstance(loaded_classes, list):
                    self.classes = loaded_classes

                raw_mapping = self.metadata.get("class_mapping", {})
                if raw_mapping:
                    self.class_mapping = {int(k): str(v) for k, v in raw_mapping.items()}
            else:
                self.metadata = {
                    "model": "XGBoost",
                    "version": self.version,
                    "classes": self.classes,
                    "features": [
                        "Conflicting_Files_Count",
                        "Author_Match",
                        "Lines_Changed_Local",
                        "Lines_Changed_Incoming",
                        "Total_Lines_Changed",
                        "Conflict_Chunk_Count",
                        "Avg_Chunk_Size",
                        "Local_Conflict_Lines",
                        "Incoming_Conflict_Lines",
                        "Local_Incoming_Ratio",
                        "Primary_File_Type",
                        "Time_Diff_Hours",
                    ],
                    "algorithm": "XGBoost",
                }

            self.is_loaded = True
            self.load_error = None
            return True

        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            self.model = None
            return False

    def predict(self, features_df: pd.DataFrame) -> List[str]:
        """
        Returns list of predicted human-readable class names.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError(f"Model is not loaded. Error: {self.load_error}")

        raw_preds = self.model.predict(features_df)
        return [self.class_mapping.get(int(idx), str(idx)) for idx in raw_preds]

    def predict_proba(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Returns predicted probabilities array from model.predict_proba().
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError(f"Model is not loaded. Error: {self.load_error}")

        return self.model.predict_proba(features_df)

    def predict_single(self, features_df: pd.DataFrame) -> PredictionResponse:
        """
        Executes inference for a single input row and returns a PredictionResponse
        containing human-readable prediction, confidence (probability of predicted class),
        and full probability distribution.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError(f"Model is not loaded. Error: {self.load_error}")

        probs = self.predict_proba(features_df)[0]

        # Map each class index to its probability
        # Standard classes: keep_local, keep_incoming, combine_both
        probabilities: Dict[str, float] = {}
        for idx, prob in enumerate(probs):
            class_name = self.class_mapping.get(idx, f"class_{idx}")
            probabilities[class_name] = round(float(prob), 4)

        # Predicted class is argmax of probabilities
        predicted_idx = int(np.argmax(probs))
        predicted_class = self.class_mapping.get(predicted_idx, self.classes[predicted_idx])
        confidence = probabilities[predicted_class]

        return PredictionResponse(
            prediction=predicted_class,
            confidence=confidence,
            probabilities=probabilities,
            model_version=self.version,
        )

    def get_model_info(self) -> ModelInfoResponse:
        """
        Returns model metadata, feature order, and classes.
        """
        features = self.metadata.get(
            "features",
            [
                "Conflicting_Files_Count",
                "Author_Match",
                "Lines_Changed_Local",
                "Lines_Changed_Incoming",
                "Total_Lines_Changed",
                "Conflict_Chunk_Count",
                "Avg_Chunk_Size",
                "Local_Conflict_Lines",
                "Incoming_Conflict_Lines",
                "Local_Incoming_Ratio",
                "Primary_File_Type",
                "Time_Diff_Hours",
            ],
        )

        return ModelInfoResponse(
            model=self.metadata.get("model", "XGBoost"),
            version=self.version,
            features=features,
            classes=self.classes,
            algorithm=self.metadata.get("algorithm", "XGBoost"),
            metrics=self.metadata.get("metrics"),
        )


# Global singleton instance for application lifespan
model_service = ModelService()
