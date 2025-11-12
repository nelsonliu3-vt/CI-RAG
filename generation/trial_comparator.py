"""
Trial Comparator Module
Generates structured trial comparison tables
TODO: Expand with LLM-based structured extraction
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from generation.analyst import get_analyst

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrialComparator:
    """Generates trial comparison tables"""

    def __init__(self):
        self.analyst = get_analyst()

    def generate_comparison_table(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate structured trial comparison table

        Args:
            query: Comparison query
            contexts: Retrieved documents

        Returns:
            Dict with table data and markdown
        """
        try:
            # Generate markdown table
            markdown_table = self.analyst.generate_comparison(query, contexts)

            # Parse markdown table into structured data
            structured_data = self._parse_markdown_table(markdown_table)

            return {
                "markdown": markdown_table,
                "data": structured_data,
                "query": query,
                "num_sources": len(contexts)
            }

        except Exception as e:
            logger.error(f"Error generating comparison table: {e}")
            return {
                "markdown": f"Error generating table: {str(e)}",
                "data": [],
                "query": query,
                "num_sources": 0
            }

    def _parse_markdown_table(self, markdown: str) -> List[Dict[str, Any]]:
        """Parse markdown table into structured data"""
        rows = []

        lines = markdown.strip().split('\n')
        header = None
        separator_found = False

        for line in lines:
            line = line.strip()

            if not line or not line.startswith('|'):
                continue

            # Split by | and clean up
            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            if not separator_found:
                if all('-' in cell or cell == '' for cell in cells):
                    separator_found = True
                    continue
                else:
                    header = cells
                    continue

            if header and len(cells) == len(header):
                row = dict(zip(header, cells))
                rows.append(row)

        logger.info(f"✓ Parsed {len(rows)} rows from markdown table")
        return rows

    def export_to_excel(self, table_data: Dict[str, Any], output_path: str) -> str:
        """
        Export table to Excel

        Args:
            table_data: Table data dict
            output_path: Output file path

        Returns:
            Path to exported file
        """
        try:
            import pandas as pd

            data = table_data.get("data", [])

            if not data:
                logger.warning("No structured data to export, saving markdown instead")
                with open(output_path.replace(".xlsx", ".md"), "w") as f:
                    f.write(table_data.get("markdown", ""))
                return output_path.replace(".xlsx", ".md")

            # Create DataFrame
            df = pd.DataFrame(data)

            # Export to Excel
            df.to_excel(output_path, index=False, engine='openpyxl')

            logger.info(f"✓ Exported table to {output_path} ({len(data)} rows)")
            return output_path

        except ImportError:
            logger.warning("pandas or openpyxl not available, falling back to markdown")
            with open(output_path.replace(".xlsx", ".md"), "w") as f:
                f.write(table_data.get("markdown", ""))
            return output_path.replace(".xlsx", ".md")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            raise

    def export_to_csv(self, table_data: Dict[str, Any], output_path: str) -> str:
        """
        Export table to CSV

        Args:
            table_data: Table data dict
            output_path: Output file path

        Returns:
            Path to exported file
        """
        try:
            import pandas as pd

            data = table_data.get("data", [])

            if not data:
                logger.warning("No structured data to export, saving markdown instead")
                with open(output_path.replace(".csv", ".md"), "w") as f:
                    f.write(table_data.get("markdown", ""))
                return output_path.replace(".csv", ".md")

            # Create DataFrame
            df = pd.DataFrame(data)

            # Export to CSV
            df.to_csv(output_path, index=False)

            logger.info(f"✓ Exported table to {output_path} ({len(data)} rows)")
            return output_path

        except ImportError:
            logger.warning("pandas not available, falling back to markdown")
            with open(output_path.replace(".csv", ".md"), "w") as f:
                f.write(table_data.get("markdown", ""))
            return output_path.replace(".csv", ".md")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise


# Singleton
_comparator: Optional[TrialComparator] = None


def get_trial_comparator() -> TrialComparator:
    """Get or create trial comparator singleton"""
    global _comparator
    if _comparator is None:
        _comparator = TrialComparator()
    return _comparator


if __name__ == "__main__":
    print("Testing Trial Comparator...")

    comparator = get_trial_comparator()

    test_contexts = [
        {
            "text": "Trial X: ORR 45%, PFS 8.2 months, n=120",
            "metadata": {"file_name": "trial_x.pdf"},
            "chunk_index": 0
        }
    ]

    table = comparator.generate_comparison_table(
        "Compare KRAS inhibitor trials",
        test_contexts
    )

    print(f"\n✓ Generated table:")
    print(f"  Sources: {table['num_sources']}")
    print(f"  Markdown length: {len(table['markdown'])} chars")

    print("\n✓ Trial Comparator test successful!")
