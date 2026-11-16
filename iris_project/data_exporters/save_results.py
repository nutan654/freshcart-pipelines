"""Persist predictions only after train_model's @test gate has passed."""
try:
    from mage_ai.data_preparation.decorators import data_exporter
except ImportError:
    def data_exporter(fn):
        return fn


@data_exporter
def export_data(df, *args, **kwargs):
    output_path = kwargs.get("output_path", "iris_predictions.csv")
    df.to_csv(output_path, index=False)
    print("Saved", len(df), "predictions to", output_path)
