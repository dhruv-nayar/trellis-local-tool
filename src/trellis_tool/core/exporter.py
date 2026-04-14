"""GLB export functionality for TRELLIS outputs."""

import logging
from pathlib import Path
from typing import Optional, Any

import trimesh
import numpy as np


logger = logging.getLogger(__name__)


class GLBExporter:
    """Handles export of TRELLIS outputs to GLB format."""

    def __init__(self, texture_size: int = 2048, optimize: bool = True, target_faces: Optional[int] = None):
        """
        Initialize the GLB exporter.

        Args:
            texture_size: Target texture resolution
            optimize: Whether to optimize the mesh
            target_faces: Target face count for optimization (None = auto)
        """
        self.texture_size = texture_size
        self.optimize = optimize
        self.target_faces = target_faces

    def export(self, outputs: dict, output_path: Path) -> Path:
        """
        Export TRELLIS outputs to GLB file.

        Args:
            outputs: Dictionary containing TRELLIS pipeline outputs
            output_path: Path to save the GLB file

        Returns:
            Path to the exported GLB file
        """
        logger.info(f"Exporting to GLB: {output_path}")

        try:
            # Extract mesh from outputs
            mesh_data = self._extract_mesh(outputs)

            if mesh_data is None:
                raise ValueError("No mesh data found in outputs")

            # Create trimesh object
            mesh = self._create_trimesh(mesh_data)

            # Optimize if requested
            if self.optimize:
                mesh = self._optimize_mesh(mesh)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Export to GLB
            mesh.export(str(output_path), file_type="glb")

            file_size = output_path.stat().st_size / 1e6
            logger.info(f"✓ Exported GLB: {output_path} ({file_size:.2f} MB)")

            return output_path

        except Exception as e:
            logger.error(f"Failed to export GLB: {e}")
            raise

    def _extract_mesh(self, outputs: dict) -> Optional[dict]:
        """
        Extract mesh data from TRELLIS outputs.

        Args:
            outputs: TRELLIS pipeline outputs

        Returns:
            Dictionary with mesh data (vertices, faces, colors, etc.)
        """
        # TRELLIS outputs contain 'gaussian', 'radiance_field', and 'mesh'
        if "mesh" in outputs:
            return outputs["mesh"]

        logger.warning("No mesh found in outputs, attempting to extract from radiance field")

        # Fallback: try to extract from radiance field or gaussians
        if "radiance_field" in outputs:
            # Note: This requires TRELLIS-specific extraction
            # The actual implementation depends on TRELLIS internal structure
            logger.info("Extracting mesh from radiance field...")
            return self._extract_from_radiance_field(outputs["radiance_field"])

        return None

    def _extract_from_radiance_field(self, radiance_field: Any) -> Optional[dict]:
        """
        Extract mesh from radiance field.

        Args:
            radiance_field: TRELLIS radiance field output

        Returns:
            Mesh data dictionary
        """
        # This is a placeholder - actual implementation depends on TRELLIS API
        # TRELLIS should provide methods to convert radiance fields to meshes
        try:
            # Assuming TRELLIS provides an extraction method
            if hasattr(radiance_field, 'extract_mesh'):
                mesh_data = radiance_field.extract_mesh()
                return mesh_data
        except Exception as e:
            logger.error(f"Failed to extract mesh from radiance field: {e}")

        return None

    def _create_trimesh(self, mesh_data: dict) -> trimesh.Trimesh:
        """
        Create a trimesh object from mesh data.

        Args:
            mesh_data: Dictionary with vertices, faces, and optionally colors/uvs

        Returns:
            Trimesh object
        """
        vertices = mesh_data.get("vertices")
        faces = mesh_data.get("faces")

        if vertices is None or faces is None:
            raise ValueError("Mesh data missing vertices or faces")

        # Convert to numpy arrays if needed
        if not isinstance(vertices, np.ndarray):
            vertices = np.array(vertices)
        if not isinstance(faces, np.ndarray):
            faces = np.array(faces)

        # Create base mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        # Add vertex colors if available
        if "colors" in mesh_data:
            colors = mesh_data["colors"]
            if not isinstance(colors, np.ndarray):
                colors = np.array(colors)
            mesh.visual.vertex_colors = colors

        # Add UV coordinates and texture if available
        if "uv" in mesh_data and "texture" in mesh_data:
            mesh.visual = trimesh.visual.TextureVisuals(
                uv=mesh_data["uv"],
                image=mesh_data["texture"]
            )

        logger.debug(f"Created mesh: {len(vertices)} vertices, {len(faces)} faces")

        # Correct TRELLIS orientation: models are generated lying on their back.
        # Apply a -90 degree rotation around the X axis so they stand upright.
        rotation = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
        mesh.apply_transform(rotation)

        return mesh

    def _optimize_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """
        Optimize mesh by simplifying geometry.

        Args:
            mesh: Input trimesh object

        Returns:
            Optimized trimesh object
        """
        original_faces = len(mesh.faces)

        logger.info(f"Optimizing mesh (original: {original_faces:,} faces)")

        try:
            # Remove duplicate vertices
            mesh.merge_vertices()

            # Remove degenerate faces
            mesh.remove_degenerate_faces()

            # Simplify if target faces specified
            if self.target_faces and len(mesh.faces) > self.target_faces:
                mesh = mesh.simplify_quadric_decimation(self.target_faces)

            optimized_faces = len(mesh.faces)
            reduction = (1 - optimized_faces / original_faces) * 100

            logger.info(f"✓ Optimized: {optimized_faces:,} faces ({reduction:.1f}% reduction)")

        except Exception as e:
            logger.warning(f"Optimization failed, using original mesh: {e}")

        return mesh

    def export_alternative_formats(self, mesh: trimesh.Trimesh, output_path: Path, formats: list = ["obj", "ply"]):
        """
        Export mesh to alternative formats.

        Args:
            mesh: Trimesh object to export
            output_path: Base output path (extension will be changed)
            formats: List of formats to export
        """
        for fmt in formats:
            fmt_path = output_path.with_suffix(f".{fmt}")
            try:
                mesh.export(str(fmt_path), file_type=fmt)
                logger.info(f"✓ Exported {fmt.upper()}: {fmt_path}")
            except Exception as e:
                logger.warning(f"Failed to export {fmt.upper()}: {e}")
